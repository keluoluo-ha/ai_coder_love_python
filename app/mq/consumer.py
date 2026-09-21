import logging
import signal
import threading

import pika

from app.config import RABBITMQ_URL
from app.mq.event import EmotionalCareEvent
from app.mq.publisher import QUEUE_NAME
from app.services.emotional_care_post_process import EmotionalCarePostProcessService, generate_care_copy

logger = logging.getLogger(__name__)


class EmotionalCareEventConsumer:
    def __init__(self, url: str | None = None, queue_name: str = QUEUE_NAME, post_process=None):
        self.url = url or RABBITMQ_URL
        if not self.url:
            raise RuntimeError("RABBITMQ_URL is not configured")
        self.queue_name = queue_name
        self.post_process = post_process or EmotionalCarePostProcessService()
        self._stopping = threading.Event()
        self._connection = None

    def stop(self) -> None:
        self._stopping.set()
        if self._connection and self._connection.is_open:
            self._connection.add_callback_threadsafe(self._connection.close)

    def run_forever(self) -> None:
        parameters = pika.URLParameters(self.url)
        parameters.heartbeat = 30
        parameters.blocked_connection_timeout = 10
        while not self._stopping.is_set():
            try:
                self._connection = pika.BlockingConnection(parameters)
                channel = self._connection.channel()
                channel.queue_declare(queue=self.queue_name, durable=True)
                channel.basic_qos(prefetch_count=1)
                channel.basic_consume(queue=self.queue_name, on_message_callback=self._on_message, auto_ack=False)
                logger.info("emotional care consumer started queue=%s", self.queue_name)
                channel.start_consuming()
            except Exception:
                if not self._stopping.is_set():
                    logger.exception("emotional care consumer connection failed; retrying")
                    self._stopping.wait(5)
            finally:
                if self._connection and self._connection.is_open:
                    self._connection.close()
                self._connection = None

    def _on_message(self, channel, method, properties, body: bytes) -> None:
        try:
            event = EmotionalCareEvent.from_bytes(body)
            care_copy = generate_care_copy(event)
            self.post_process.handle(event, care_copy)
            logger.info("processed emotional care event id=%s copy=%s", event.event_id, care_copy)
        except Exception:
            logger.exception("failed emotional care event delivery_tag=%s", method.delivery_tag)
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            return
        channel.basic_ack(delivery_tag=method.delivery_tag)


def main() -> None:
    consumer = EmotionalCareEventConsumer()

    def request_stop(*_args):
        consumer.stop()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    consumer.run_forever()


if __name__ == "__main__":
    main()
