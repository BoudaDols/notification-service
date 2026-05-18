# notification-service — Technical Documentation

## Overview

`notification-service` is a stateless, event-driven microservice. It consumes events from Kafka and sends transactional emails to users via SMTP. It exposes a single HTTP endpoint (`/health`) used by Kubernetes probes.

It has no database and no direct HTTP communication with other services. All input comes from Kafka. All output goes to the SMTP server.

---

## Architecture

```
abonnement ──publishes──► Kafka: subscription.changed
                                       │
api-gateway ─publishes──► Kafka: user.registered (future)
                                       │
                           ┌───────────┘
                           ▼
              notification-service
              (Kafka consumer thread)
                           │
                           ▼
                    SMTP (Mailtrap)
                           │
                           ▼
                    User inbox
```

**Communication pattern:**
- Input: Kafka consumer (async, pull-based)
- Output: SMTP (sync, per-event)
- Health: Flask HTTP `/health` (for Kubernetes probes only)

---

## Kafka Topics

### `subscription.changed`

Published by `abonnement` when a subscription is created or canceled.

**Event payload**

| Field | Type | Description |
|---|---|---|
| `event` | string | `subscription.created` or `subscription.canceled` |
| `subscription_id` | integer | ID of the subscription |
| `user_id` | integer | ID of the user |
| `user_email` | string | Email address of the user (optional — falls back to `DEFAULT_RECIPIENT`) |
| `plan_name` | string | Name of the plan (e.g. `Basic`) |
| `plan_type` | string | `free` or `paid` |
| `status` | string | `active`, `pending`, or `canceled` |
| `starts_at` | string | Subscription start date (ISO 8601) |
| `ends_at` | string | Subscription end date (ISO 8601) |

**Example — subscription created**
```json
{
  "event": "subscription.created",
  "subscription_id": 12,
  "user_id": 42,
  "user_email": "alice@example.com",
  "plan_name": "Basic",
  "plan_type": "paid",
  "status": "pending",
  "starts_at": "2026-05-18T10:00:00",
  "ends_at": "2026-06-18T10:00:00"
}
```

**Example — subscription canceled**
```json
{
  "event": "subscription.canceled",
  "subscription_id": 12,
  "user_id": 42,
  "user_email": "alice@example.com",
  "plan_name": "Basic",
  "status": "canceled"
}
```

---

### `payment.succeeded`

Published by `abonnement` when a payment is confirmed (direct payment or via Stripe/PayPal webhook).

**Event payload**

| Field | Type | Description |
|---|---|---|
| `event` | string | `payment.succeeded` |
| `payment_id` | integer | ID of the payment record |
| `subscription_id` | integer | ID of the related subscription |
| `user_id` | integer | ID of the user |
| `user_email` | string | Email address of the user (optional) |
| `amount` | string | Amount charged (e.g. `"9.99"`) |
| `currency` | string | Currency code (e.g. `"usd"`) |
| `transaction_id` | string | Gateway transaction ID |
| `paid_at` | string | Payment timestamp (ISO 8601) |

**Example**
```json
{
  "event": "payment.succeeded",
  "payment_id": 7,
  "subscription_id": 12,
  "user_id": 42,
  "user_email": "alice@example.com",
  "amount": "9.99",
  "currency": "usd",
  "transaction_id": "pi_stripe_abc123",
  "paid_at": "2026-05-18T10:05:00"
}
```

---

### `payment.failed`

Published by `abonnement` when a payment fails via Stripe or PayPal webhook.

**Event payload**

| Field | Type | Description |
|---|---|---|
| `event` | string | `payment.failed` |
| `payment_id` | integer | ID of the payment record |
| `subscription_id` | integer | ID of the related subscription |
| `user_id` | integer | ID of the user |
| `user_email` | string | Email address of the user (optional) |
| `amount` | string | Amount that was attempted |
| `transaction_id` | string | Gateway transaction ID |

**Example**
```json
{
  "event": "payment.failed",
  "payment_id": 8,
  "subscription_id": 12,
  "user_id": 42,
  "user_email": "alice@example.com",
  "amount": "9.99",
  "transaction_id": "pi_stripe_xyz789"
}
```

---

## Email Notifications

### Subscription confirmed

- **Trigger**: `subscription.created` event
- **Subject**: `Your subscription is confirmed`
- **Template**: `src/templates/subscription_created.txt`
- **Variables**: `plan_name`, `starts_at`, `ends_at`

---

### Subscription canceled

- **Trigger**: `subscription.canceled` event
- **Subject**: `Your subscription has been canceled`
- **Template**: `src/templates/subscription_canceled.txt`
- **Variables**: `plan_name`

---

### Payment receipt

- **Trigger**: `payment.succeeded` event
- **Subject**: `Payment receipt — thank you`
- **Template**: `src/templates/payment_succeeded.txt`
- **Variables**: `amount`, `currency`, `transaction_id`, `paid_at`

---

### Payment failed

- **Trigger**: `payment.failed` event
- **Subject**: `Your payment failed — please retry`
- **Template**: `src/templates/payment_failed.txt`
- **Variables**: `amount`, `transaction_id`

---

## HTTP Endpoint

### Health check

Used by Kubernetes liveness and readiness probes. Returns `200 OK` when the Flask process is running.

```
GET /health
```

**Response 200**
```json
{
  "status": "ok"
}
```

---

## Event Routing

Events are routed in `src/handlers.py` via a simple dispatch table:

```python
EVENT_HANDLERS = {
    "subscription.created":  handle_subscription_created,
    "subscription.canceled": handle_subscription_canceled,
    "payment.succeeded":     handle_payment_succeeded,
    "payment.failed":        handle_payment_failed,
}
```

Unknown events are logged at `DEBUG` level and silently ignored — they do not cause errors.

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| Kafka broker unreachable at startup | Consumer thread logs the error and exits — Flask health endpoint still responds |
| Malformed JSON message | Logged as warning, message skipped, consumer continues |
| Message missing `event` field | Logged as warning, message skipped, consumer continues |
| SMTP server unreachable | Exception logged as error, consumer continues with next message |
| Unknown event type | Logged at DEBUG level, silently ignored |

The consumer loop is designed to never crash on bad data. Only a Kafka broker failure or an unhandled exception in the consumer infrastructure itself will stop the thread.

---

## Configuration

All configuration is provided via environment variables. In Kubernetes, non-sensitive values come from the `ConfigMap` and sensitive values from the `Secret`.

| Variable | Source | Description |
|---|---|---|
| `KAFKA_BROKERS` | ConfigMap | Kafka broker address — `kafka:9092` in cluster |
| `KAFKA_ENABLED` | ConfigMap | Set to `false` to disable the consumer (e.g. for testing) |
| `SMTP_HOST` | ConfigMap | SMTP server hostname |
| `SMTP_PORT` | ConfigMap | SMTP server port |
| `MAIL_FROM` | ConfigMap | Sender address shown in emails |
| `SMTP_USER` | Secret | SMTP username |
| `SMTP_PASS` | Secret | SMTP password |
| `DEFAULT_RECIPIENT` | Secret | Fallback email when `user_email` is absent from the event |

---

## Network Policy

The service has strict egress rules — it can only reach:
- Kafka pods on port `9092`
- External SMTP servers on ports `2525`, `587`, `465`
- DNS on UDP port `53`

No other service in the cluster calls `notification-service` directly. Ingress is limited to the health check port `5000`.

---

## Deployment

### Local (Docker Desktop)

```bash
# Build
docker build -t notification-service:latest .

# Fill in SMTP credentials
# Edit k8s/local/secret.yaml

# Deploy
kubectl apply -f k8s/local/

# Check logs
kubectl logs -l app=notification-service -f
```

### Production (EKS / AKS)

Deployment is handled by the CD pipeline on push to `main`. The pipeline:
1. Builds and pushes the Docker image to DockerHub
2. Creates/updates the `notification-secrets` Kubernetes secret
3. Applies `k8s/` manifests
4. Rolls out the new image with `kubectl set image`

---

## Testing

Tests use `unittest.mock` — no real Kafka or SMTP connection is needed.

```bash
KAFKA_ENABLED=false pytest tests/ -v
```

| Test file | What it covers |
|---|---|
| `tests/test_handlers.py` | One test per event type, fallback recipient, unknown event, health endpoint |
| `tests/test_consumer.py` | Valid message dispatch, invalid JSON, missing event field, handler crash resilience |
