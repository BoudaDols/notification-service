import json
import logging
import os
import threading
from confluent_kafka import Consumer, KafkaError, KafkaException
from src.handlers import dispatch
from src.mailer import Mailer

logger = logging.getLogger(__name__)

TOPICS = ["subscription.changed", "payment.succeeded", "payment.failed"]


def _build_consumer() -> Consumer:
    return Consumer({
        "bootstrap.servers": os.environ.get("KAFKA_BROKERS", "kafka:9092"),
        "group.id": "notification-service",
        # Start from earliest so no events are missed on first boot
        "auto.offset.reset": "earliest",
        "enable.auto.commit": True,
    })


def _process_message(msg, mailer: Mailer) -> None:
    """Decode a Kafka message and dispatch to the right handler."""
    try:
        data = json.loads(msg.value().decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.warning(f"Could not decode message from {msg.topic()}: {e}")
        return

    event = data.get("event")
    if not event:
        logger.warning(f"Message on {msg.topic()} has no 'event' field — skipping")
        return

    logger.info(f"Received event: {event}")
    try:
        dispatch(event, data, mailer)
    except Exception as e:
        # Log but don't crash the consumer loop — bad events should not
        # stop the service from processing subsequent messages.
        logger.error(f"Handler failed for event '{event}': {e}")


def run_consumer() -> None:
    """Main consumer loop. Runs indefinitely, meant to run in a thread."""
    mailer = Mailer()
    consumer = _build_consumer()
    consumer.subscribe(TOPICS)
    logger.info(f"Kafka consumer started — subscribed to: {TOPICS}")

    try:
        while True:
            msg = consumer.poll(timeout=1.0)

            if msg is None:
                continue

            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    # End of partition — not an error, just no new messages
                    continue
                raise KafkaException(msg.error())

            _process_message(msg, mailer)

    except Exception as e:
        logger.error(f"Consumer loop crashed: {e}")
    finally:
        consumer.close()
        logger.info("Kafka consumer closed")


def start_consumer_thread() -> threading.Thread:
    """Start the consumer loop in a daemon thread."""
    thread = threading.Thread(target=run_consumer, daemon=True, name="kafka-consumer")
    thread.start()
    return thread
