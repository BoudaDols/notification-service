"""
Tests for event handlers — verify the right email is sent for each event.
The Mailer is mocked so no real SMTP connection is made.
"""
from unittest.mock import MagicMock, patch
import pytest
from src.handlers import dispatch


@pytest.fixture
def mailer():
    return MagicMock()


class TestDispatch:
    def test_unknown_event_is_ignored(self, mailer):
        """Unknown events should not raise and should not send any email."""
        dispatch("unknown.event", {}, mailer)
        mailer.send.assert_not_called()

    def test_subscription_created_sends_email(self, mailer):
        data = {
            "event": "subscription.created",
            "user_email": "user@example.com",
            "plan_name": "Basic",
            "starts_at": "2026-05-18",
            "ends_at": "2026-06-18",
        }
        dispatch("subscription.created", data, mailer)
        mailer.send.assert_called_once()
        call_kwargs = mailer.send.call_args[1]
        assert call_kwargs["to"] == "user@example.com"
        assert "confirmed" in call_kwargs["subject"].lower()
        assert "Basic" in call_kwargs["body"]

    def test_subscription_canceled_sends_email(self, mailer):
        data = {
            "event": "subscription.canceled",
            "user_email": "user@example.com",
            "plan_name": "Pro",
        }
        dispatch("subscription.canceled", data, mailer)
        mailer.send.assert_called_once()
        call_kwargs = mailer.send.call_args[1]
        assert call_kwargs["to"] == "user@example.com"
        assert "canceled" in call_kwargs["subject"].lower()
        assert "Pro" in call_kwargs["body"]

    def test_payment_succeeded_sends_email(self, mailer):
        data = {
            "event": "payment.succeeded",
            "user_email": "user@example.com",
            "amount": "9.99",
            "currency": "usd",
            "transaction_id": "txn_123",
            "paid_at": "2026-05-18T10:00:00",
        }
        dispatch("payment.succeeded", data, mailer)
        mailer.send.assert_called_once()
        call_kwargs = mailer.send.call_args[1]
        assert call_kwargs["to"] == "user@example.com"
        assert "receipt" in call_kwargs["subject"].lower()
        assert "9.99" in call_kwargs["body"]
        assert "txn_123" in call_kwargs["body"]

    def test_payment_failed_sends_email(self, mailer):
        data = {
            "event": "payment.failed",
            "user_email": "user@example.com",
            "amount": "4.99",
            "transaction_id": "txn_456",
        }
        dispatch("payment.failed", data, mailer)
        mailer.send.assert_called_once()
        call_kwargs = mailer.send.call_args[1]
        assert call_kwargs["to"] == "user@example.com"
        assert "failed" in call_kwargs["subject"].lower()
        assert "4.99" in call_kwargs["body"]

    def test_falls_back_to_default_recipient_when_no_email(self, mailer):
        """When user_email is missing, DEFAULT_RECIPIENT env var is used."""
        data = {"event": "subscription.created", "plan_name": "Free"}
        with patch.dict("os.environ", {"DEFAULT_RECIPIENT": "fallback@example.com"}):
            dispatch("subscription.created", data, mailer)
        call_kwargs = mailer.send.call_args[1]
        assert call_kwargs["to"] == "fallback@example.com"


class TestHealthEndpoint:
    def test_health_returns_ok(self):
        import os
        os.environ["KAFKA_ENABLED"] = "false"
        from app import app
        client = app.test_client()
        response = client.get("/health")
        assert response.status_code == 200
        assert response.get_json() == {"status": "ok"}
