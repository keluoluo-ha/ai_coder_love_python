import logging
import os

import pika

from app.config import RABBITMQ_URL
from app.mq.event import EmotionalCareEvent

logger = logging.getLogger(__name__)
QUEUE_NAME = "emotional_care_events"


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
            channel.queue_declare(queue=self.queue_name, durable=True)
            channel.basic_publish(
                exchange="",
                routing_key=self.queue_name,
                body=event.to_bytes(),
                properties=pika.BasicProperties(
                    content_type="application/json",
                    delivery_mode=pika.DeliveryMode.Persistent,
                    message_id=event.event_id,
                    type=event.event_type,
                ),
            )
        finally:
            connection.close()

    def publish_consultation_completed(self, consultation_id: int, user_id: str) -> None:
        self.publish(EmotionalCareEvent.consultation_completed(consultation_id, user_id))

    def publish_follow_up_completed(self, follow_up_id: int, consultation_id: int, user_id: str) -> None:
        self.publish(EmotionalCareEvent.follow_up_completed(follow_up_id, consultation_id, user_id))
