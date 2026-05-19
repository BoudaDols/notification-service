import json
import logging
import os
import threading
from kafka import KafkaConsumer
from kafka.errors import KafkaError
from src.handlers import dispatch
from src.mailer import Mailer

logger = logging.getLogger(__name__)

TOPICS = ["subscription.changed", "payment.succeeded", "payment.failed",
          "user.registered", "user.login"]


def _build_consumer() -> KafkaConsumer:
    return KafkaConsumer(
        *TOPICS,
        bootstrap_servers=os.environ.get("KAFKA_BROKERS", "kafka:9092"),
        group_id="notification-service",
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=lambda v: v,  # raw bytes — we decode manually
        api_version=(2, 5, 0),  # Skip version probe — compatible with Kafka 3.7
    )


def _process_message(msg, mailer: Mailer) -> None:
    """Decode a Kafka message and dispatch to the right handler."""
    try:
        data = json.loads(msg.value.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.warning(f"Could not decode message from {msg.topic}: {e}")
        return

    event = data.get("event")
    if not event:
        logger.warning(f"Message on {msg.topic} has no 'event' field — skipping")
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
    logger.info(f"Kafka consumer started — subscribed to: {TOPICS}")

    try:
        consumer = _build_consumer()
        for msg in consumer:
            _process_message(msg, mailer)
    except KafkaError as e:
        logger.error(f"Kafka error: {e}")
    except Exception as e:
        logger.error(f"Consumer loop crashed: {e}")
    finally:
        logger.info("Kafka consumer stopped")


def start_consumer_thread() -> threading.Thread:
    """Start the consumer loop in a daemon thread."""
    thread = threading.Thread(target=run_consumer, daemon=True, name="kafka-consumer")
    thread.start()
    return thread
