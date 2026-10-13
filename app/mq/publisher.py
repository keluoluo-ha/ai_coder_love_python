"""生产端：发布情感关怀事件 + 声明延迟消息拓扑。

可靠性要点：
- 队列 durable=True、消息 delivery_mode=Persistent：都落盘，Broker 重启不丢消息。
- message_id=event_id：作为幂等键传给 Broker 和下游。
- 发布为短连接（建连即发即关）：低频事件场景开销可忽略，代码最简；高 QPS 再换连接池 + publisher confirm。
延迟提醒：TTL + 死信路由原生方案（不依赖 rabbitmq_delayed_message_exchange 插件），见 publish_follow_up_reminder。
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


def declare_delay_topology(channel) -> None:
    """声明延迟消息拓扑：提醒队列 + 死信等待队列。

    等待队列无消费者，配 x-dead-letter-exchange="" + x-dead-letter-routing-key=提醒队列，
    消息 TTL 到期自动变为死信，经默认交换机路由到 REMINDER_QUEUE，由消费者到点收到。
    用默认交换机("")而非自定义 exchange：路由即队列名，拓扑更简单。
    """
    channel.queue_declare(queue=REMINDER_QUEUE, durable=True)
    channel.queue_declare(
        queue=WAIT_QUEUE,
        durable=True,
        arguments={
            "x-dead-letter-exchange": "",
            "x-dead-letter-routing-key": REMINDER_QUEUE,
        },
    )


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
            channel.queue_declare(queue=self.queue_name, durable=True)  # 队列落盘
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
            declare_delay_topology(channel)
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
