"""
Tests for the consumer message processing logic.
kafka is mocked at import time so tests run without a real Kafka broker.
"""
import sys
from unittest.mock import MagicMock, patch

# Mock kafka before importing the consumer module
sys.modules["kafka"] = MagicMock()
sys.modules["kafka.errors"] = MagicMock()

from src.consumer import _process_message  # noqa: E402


def _make_msg(value: bytes, topic: str = "subscription.changed"):
    msg = MagicMock()
    msg.value = value  # kafka-python uses attribute, not method
    msg.topic = topic
    return msg


class TestProcessMessage:
    def test_valid_message_dispatches_event(self):
        msg = _make_msg(b'{"event": "subscription.created", "plan_name": "Basic"}')
        mailer = MagicMock()
        with patch("src.consumer.dispatch") as mock_dispatch:
            _process_message(msg, mailer)
            mock_dispatch.assert_called_once_with(
                "subscription.created",
                {"event": "subscription.created", "plan_name": "Basic"},
                mailer,
            )

    def test_invalid_json_is_skipped(self):
        msg = _make_msg(b"not-json")
        mailer = MagicMock()
        with patch("src.consumer.dispatch") as mock_dispatch:
            _process_message(msg, mailer)
            mock_dispatch.assert_not_called()

    def test_message_without_event_field_is_skipped(self):
        msg = _make_msg(b'{"user_id": 42}')
        mailer = MagicMock()
        with patch("src.consumer.dispatch") as mock_dispatch:
            _process_message(msg, mailer)
            mock_dispatch.assert_not_called()

    def test_handler_exception_does_not_crash_consumer(self):
        msg = _make_msg(b'{"event": "payment.succeeded"}')
        mailer = MagicMock()
        with patch("src.consumer.dispatch", side_effect=Exception("SMTP down")):
            # Should not raise
            _process_message(msg, mailer)
