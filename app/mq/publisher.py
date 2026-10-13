"""生产端：发布情感关怀事件 + 声明 MQ 拓扑（含延迟 + 死信兜底）。

可靠性要点：
- 队列 durable=True、消息 delivery_mode=Persistent：都落盘，Broker 重启不丢消息。
- message_id=event_id：作为幂等键传给 Broker 和下游。
- publisher confirm：confirm_delivery() 后 basic_publish 会等 Broker 确认落盘，未确认抛异常可重发。
- 发布为短连接（建连即发即关）：低频事件场景开销可忽略，代码最简；高 QPS 再换连接池。
延迟提醒：TTL + 死信路由原生方案（不依赖 rabbitmq_delayed_message_exchange 插件），见 publish_follow_up_reminder。
死信兜底：主队列配 x-dead-letter-exchange 指向 DLQ，消费失败 nack(requeue=False) 进 DLQ 不再无限回队。
"""
import logging
import os
from datetime import datetime, timezone

import pika

from app.config import RABBITMQ_URL
from app.mq.event import EmotionalCareEvent

logger = logging.getLogger(__name__)
QUEUE_NAME = "emotional_care_events"
REMINDER_QUEUE = "emotional_care_reminders"
# 无消费者的等待队列：消息在此按 per-message TTL 停留，到期后经死信路由投递到 REMINDER_QUEUE
WAIT_QUEUE = "emotional_care_delay_wait"
# 死信交换机 + 各队列的死信告警队列(DLQ)：消费失败的消息进 DLQ，不再无限回队
DLQ_EXCHANGE = "emotional_care_dlx"
EVENTS_DLQ = "emotional_care_events_dlq"
REMINDER_DLQ = "emotional_care_reminders_dlq"


def declare_topology(channel) -> None:
    """声明完整拓扑：events/reminders 主队列 + 各自 DLQ + 延迟等待队列。

    主队列配 x-dead-letter-exchange=DLQ_EXCHANGE：消费失败时 nack(requeue=False) 让消息进 DLQ。
    WAIT_QUEUE 用默认交换机("")死信到 REMINDER_QUEUE：这是延迟投递机制(TTL 到期变死信)。
    注意：队列 args 变更后，已存在的旧队列会因 inequivalent args 报错，需先删旧队列(全新 Broker 无此问题)。
    """
    channel.exchange_declare(exchange=DLQ_EXCHANGE, exchange_type="direct", durable=True)

    # events 队列 + 其 DLQ
    channel.queue_declare(queue=EVENTS_DLQ, durable=True)
    channel.queue_bind(queue=EVENTS_DLQ, exchange=DLQ_EXCHANGE, routing_key=EVENTS_DLQ)
    channel.queue_declare(
        queue=QUEUE_NAME,
        durable=True,
        arguments={
            "x-dead-letter-exchange": DLQ_EXCHANGE,
            "x-dead-letter-routing-key": EVENTS_DLQ,
        },
    )

    # reminders 队列 + 其 DLQ
    channel.queue_declare(queue=REMINDER_DLQ, durable=True)
    channel.queue_bind(queue=REMINDER_DLQ, exchange=DLQ_EXCHANGE, routing_key=REMINDER_DLQ)
    channel.queue_declare(
        queue=REMINDER_QUEUE,
        durable=True,
        arguments={
            "x-dead-letter-exchange": DLQ_EXCHANGE,
            "x-dead-letter-routing-key": REMINDER_DLQ,
        },
    )

    # 延迟等待队列：无消费者，TTL 到期死信到 REMINDER_QUEUE（走默认交换机，routing_key 即队列名）
    channel.queue_declare(
        queue=WAIT_QUEUE,
        durable=True,
        arguments={
            "x-dead-letter-exchange": "",
            "x-dead-letter-routing-key": REMINDER_QUEUE,
        },
    )


# 兼容旧引用（consumer 原来 import declare_delay_topology）
def declare_delay_topology(channel) -> None:
    declare_topology(channel)


class EmotionalCareEventPublisher:
    def __init__(self, url: str | None = None, queue_name: str = QUEUE_NAME):
        self.url = url or RABBITMQ_URL
        if not self.url:
            raise RuntimeError("RABBITMQ_URL is not configured")
        self.queue_name = queue_name
        self.parameters = pika.URLParameters(self.url)
        self.parameters.socket_timeout = 5
        self.parameters.blocked_connection_timeout = 5

    def publish(self, event: EmotionalCareEvent) -> None:
        connection = pika.BlockingConnection(self.parameters)
        try:
            channel = connection.channel()
            declare_topology(channel)
            channel.confirm_delivery()  # 开 publisher confirm：basic_publish 会等 Broker 确认落盘
            channel.basic_publish(
                exchange="",  # 默认交换机：routing_key 即队列名
                routing_key=self.queue_name,
                body=event.to_bytes(),
                properties=pika.BasicProperties(
                    content_type="application/json",
                    delivery_mode=pika.DeliveryMode.Persistent,  # 消息落盘
                    message_id=event.event_id,  # 幂等键
                    type=event.event_type,
                ),
            )
        finally:
            connection.close()  # 短连接：低频事件，建连即发即关

    def publish_consultation_completed(self, consultation_id: int, user_id: str) -> None:
        self.publish(EmotionalCareEvent.consultation_completed(consultation_id, user_id))

    def publish_follow_up_completed(self, follow_up_id: int, consultation_id: int, user_id: str) -> None:
        self.publish(EmotionalCareEvent.follow_up_completed(follow_up_id, consultation_id, user_id))

    def publish_follow_up_reminder(
        self, follow_up_id: int, consultation_id: int, user_id: str, fire_at: datetime
    ) -> None:
        """发布一条延迟提醒：到 fire_at 时刻由死信机制投递给提醒消费者。

        - fire_at 在未来：发到 WAIT_QUEUE，per-message TTL = (fire_at - now)；
        - fire_at 已过期：直接发到 REMINDER_QUEUE 立即消费。
        注意：RabbitMQ 只检查队头消息过期，per-message TTL 在队头阻塞时会延迟投递；
        低频回访场景可接受，高并发可按延迟档位拆多个等待队列。
        """
        event = EmotionalCareEvent.follow_up_reminder(follow_up_id, consultation_id, user_id)
        now = datetime.now(timezone.utc)
        fire = fire_at if fire_at.tzinfo else fire_at.replace(tzinfo=timezone.utc)
        ttl_ms = max(0, int((fire - now).total_seconds() * 1000))

        connection = pika.BlockingConnection(self.parameters)
        try:
            channel = connection.channel()
            declare_topology(channel)
            channel.confirm_delivery()  # publisher confirm：确认延迟消息已落盘
            target_queue = WAIT_QUEUE if ttl_ms > 0 else REMINDER_QUEUE
            basic_props = {
                "content_type": "application/json",
                "delivery_mode": pika.DeliveryMode.Persistent,
                "message_id": event.event_id,
                "type": event.event_type,
            }
            if ttl_ms > 0:
                basic_props["expiration"] = str(ttl_ms)
            channel.basic_publish(
                exchange="",
                routing_key=target_queue,
                body=event.to_bytes(),
                properties=pika.BasicProperties(**basic_props),
            )
            logger.info(
                "scheduled follow-up reminder follow_up=%s target=%s ttl_ms=%s",
                follow_up_id, target_queue, ttl_ms,
            )
        finally:
            connection.close()
