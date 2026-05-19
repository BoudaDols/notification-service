import logging
import os
from pathlib import Path
from src.mailer import Mailer

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"


def _load_template(name: str) -> str:
    path = TEMPLATES_DIR / name
    return path.read_text(encoding="utf-8")


def _get_recipient(data: dict) -> str:
    """Extract user email from event data, fall back to default."""
    return data.get("user_email") or os.environ.get("DEFAULT_RECIPIENT", "user@example.com")


def handle_subscription_created(data: dict, mailer: Mailer) -> None:
    recipient = _get_recipient(data)
    body = _load_template("subscription_created.txt").format(
        plan_name=data.get("plan_name", "N/A"),
        starts_at=data.get("starts_at", "N/A"),
        ends_at=data.get("ends_at", "N/A"),
    )
    mailer.send(
        to=recipient,
        subject="Your subscription is confirmed",
        body=body,
    )


def handle_subscription_canceled(data: dict, mailer: Mailer) -> None:
    recipient = _get_recipient(data)
    body = _load_template("subscription_canceled.txt").format(
        plan_name=data.get("plan_name", "N/A"),
    )
    mailer.send(
        to=recipient,
        subject="Your subscription has been canceled",
        body=body,
    )


def handle_payment_succeeded(data: dict, mailer: Mailer) -> None:
    recipient = _get_recipient(data)
    body = _load_template("payment_succeeded.txt").format(
        amount=data.get("amount", "N/A"),
        currency=data.get("currency", "usd").upper(),
        transaction_id=data.get("transaction_id", "N/A"),
        paid_at=data.get("paid_at", "N/A"),
    )
    mailer.send(
        to=recipient,
        subject="Payment receipt — thank you",
        body=body,
    )


def handle_payment_failed(data: dict, mailer: Mailer) -> None:
    recipient = _get_recipient(data)
    body = _load_template("payment_failed.txt").format(
        amount=data.get("amount", "N/A"),
        transaction_id=data.get("transaction_id", "N/A"),
    )
    mailer.send(
        to=recipient,
        subject="Your payment failed — please retry",
        body=body,
    )


def handle_user_registered(data: dict, mailer: Mailer) -> None:
    recipient = _get_recipient(data)
    body = _load_template("user_registered.txt").format(
        user_name=data.get("user_name", "there"),
        registered_at=data.get("registered_at", "N/A"),
    )
    mailer.send(
        to=recipient,
        subject="Welcome — your account is ready",
        body=body,
    )


def handle_user_login_success(data: dict, mailer: Mailer) -> None:
    recipient = _get_recipient(data)
    body = _load_template("user_login_success.txt").format(
        user_name=data.get("user_name", "there"),
        logged_in_at=data.get("logged_in_at", "N/A"),
        ip=data.get("ip", "unknown"),
    )
    mailer.send(
        to=recipient,
        subject="New login on your account",
        body=body,
    )


def handle_user_login_failed(data: dict, mailer: Mailer) -> None:
    # For failed logins, the user_email might not be in the payload
    # (since the user might not exist). Use the attempted email instead.
    recipient = data.get("user_email") or data.get("email") or os.environ.get("DEFAULT_RECIPIENT", "user@example.com")
    body = _load_template("user_login_failed.txt").format(
        email=data.get("email", "N/A"),
        failed_at=data.get("failed_at", "N/A"),
        ip=data.get("ip", "unknown"),
    )
    mailer.send(
        to=recipient,
        subject="Failed login attempt on your account",
        body=body,
    )


# Route event type to handler function
EVENT_HANDLERS = {
    "subscription.created": handle_subscription_created,
    "subscription.canceled": handle_subscription_canceled,
    "payment.succeeded": handle_payment_succeeded,
    "payment.failed": handle_payment_failed,
    "user.registered": handle_user_registered,
    "user.login_success": handle_user_login_success,
    "user.login_failed": handle_user_login_failed,
}


def dispatch(event: str, data: dict, mailer: Mailer) -> None:
    """Route an event to its handler. Unknown events are logged and ignored."""
    handler = EVENT_HANDLERS.get(event)
    if handler:
        handler(data, mailer)
    else:
        logger.debug(f"No handler for event: {event}")
