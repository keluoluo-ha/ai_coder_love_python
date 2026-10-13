"""消费端：独立进程，消费咨询/回访完成事件 + 到点提醒。

部署：python -m app.mq.consumer，与 FastAPI 主进程隔离——API 挂了消息在队列里等，消费者挂了断线重连。
可靠性要点：
- auto_ack=False 手动确认：处理成功才 ack，异常 nack(requeue=True) 回队重试，消息不丢。
- heartbeat=30 防 TCP 连接假死；外层 while + wait(5) 实现断线自动重连。
- basic_qos(prefetch_count=1)：一次只给消费者 1 条，慢消费者不堆积、多实例时公平分发。
- 同时消费 events（咨询/回访完成）和 reminders（到点提醒）两个队列。
失败兜底：主队列配 x-dead-letter-exchange 指向 DLQ，消费失败 nack(requeue=False) 进 DLQ 不再无限回队；
进一步可用 TTL 重试队列做指数退避（当前为失败即进 DLQ 告警）。
"""
import logging
import signal
import threading

import pika

from app.config import RABBITMQ_URL
from app.mq.event import EmotionalCareEvent
from app.mq.publisher import QUEUE_NAME, REMINDER_QUEUE, WAIT_QUEUE, declare_topology
from app.services.emotional_care_post_process import EmotionalCarePostProcessService, generate_care_copy

logger = logging.getLogger(__name__)


class EmotionalCareEventConsumer:
    def __init__(self, url: str | None = None, queue_name: str = QUEUE_NAME, post_process=None):
        self.url = url or RABBITMQ_URL
        if not self.url:
            raise RuntimeError("RABBITMQ_URL is not configured")
        self.queue_name = queue_name
        self.post_process = post_process or EmotionalCarePostProcessService()
        self._stopping = threading.Event()  # 优雅停机信号
        self._connection = None

    def stop(self) -> None:
        """优雅停机：置停止位 + 在 pika 的事件线程里安全关闭连接。"""
        self._stopping.set()
        if self._connection and self._connection.is_open:
            # pika 的 BlockingConnection 不是线程安全的，跨线程关闭必须走 add_callback_threadsafe
            self._connection.add_callback_threadsafe(self._connection.close)

    def run_forever(self) -> None:
        parameters = pika.URLParameters(self.url)
        parameters.heartbeat = 30  # 防 TCP 假死：30s 心跳探活
        parameters.blocked_connection_timeout = 10
        while not self._stopping.is_set():
            try:
                self._connection = pika.BlockingConnection(parameters)
                channel = self._connection.channel()
                declare_topology(channel)  # 声明主队列+DLQ+延迟队列（含 x-dead-letter 配置）
                channel.basic_qos(prefetch_count=1)  # 公平分发：每次只投 1 条给本消费者
                channel.basic_consume(queue=self.queue_name, on_message_callback=self._on_message, auto_ack=False)
                channel.basic_consume(queue=REMINDER_QUEUE, on_message_callback=self._on_reminder, auto_ack=False)
                logger.info("emotional care consumer started queues=%s,%s", self.queue_name, REMINDER_QUEUE)
                channel.start_consuming()
            except Exception:
                if not self._stopping.is_set():
                    logger.exception("emotional care consumer connection failed; retrying")
                    self._stopping.wait(5)  # 断线 5 秒后重连，避免狂重连
            finally:
                if self._connection and self._connection.is_open:
                    self._connection.close()
                self._connection = None

    def _on_message(self, channel, method, properties, body: bytes) -> None:
        """咨询/回访完成事件回调：反序列化 -> 跑业务 -> 成功 ack / 异常进 DLQ。"""
        try:
            event = EmotionalCareEvent.from_bytes(body)
            care_copy = generate_care_copy(event)
            self.post_process.handle(event, care_copy)
            logger.info("processed emotional care event id=%s copy=%s", event.event_id, care_copy)
        except Exception:
            # 失败转 DLQ（requeue=False）：消息经主队列的 x-dead-letter-exchange 进 emotional_care_events_dlq，
            # 不再无限回队；进一步可用 TTL 重试队列做指数退避（当前为失败即告警）。
            logger.exception("failed emotional care event delivery_tag=%s -> DLQ", method.delivery_tag)
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return
        channel.basic_ack(delivery_tag=method.delivery_tag)  # 成功才 ack，消息从队列移除

    def _on_reminder(self, channel, method, properties, body: bytes) -> None:
        """到点提醒回调：消息从 WAIT_QUEUE 死信路由到 REMINDER_QUEUE 后触发。"""
        try:
            event = EmotionalCareEvent.from_bytes(body)
            self.post_process.handle(event, "")
            logger.info("fired follow-up reminder id=%s follow_up=%s", event.event_id, event.follow_up_id)
        except Exception:
            # 同 _on_message：失败转 reminders_dlq，不再无限回队
            logger.exception("failed follow-up reminder delivery_tag=%s -> DLQ", method.delivery_tag)
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return
        channel.basic_ack(delivery_tag=method.delivery_tag)


def main() -> None:
    consumer = EmotionalCareEventConsumer()

    def request_stop(*_args):
        consumer.stop()

    signal.signal(signal.SIGINT, request_stop)   # Ctrl-C 优雅停机
    signal.signal(signal.SIGTERM, request_stop)  # 容器/kill 发 SIGTERM 也优雅停机
    consumer.run_forever()


if __name__ == "__main__":
    main()
