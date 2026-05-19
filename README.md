# notification-service

A lightweight Python/Flask microservice that listens to Kafka events and sends email notifications to users.

## Description

`notification-service` is a standalone microservice that reacts to domain events published by other services in the platform. It consumes events from Kafka and sends transactional emails via SMTP.

It has no database, no HTTP API beyond a health endpoint, and no direct dependency on any other service. It plugs into the existing Kafka broker and reacts to events independently — if it goes down, events queue up in Kafka and are processed when it comes back up.

### Key design decisions
- **No HTTP API**: purely event-driven, Kafka consumer only
- **No database**: stateless — no persistence needed for sending emails
- **Fault-tolerant**: Kafka failures and SMTP errors are caught and logged without crashing the consumer loop
- **KAFKA_ENABLED flag**: set to `false` to disable the consumer (useful for testing)
- **Fallback recipient**: when `user_email` is not in the event payload, falls back to `DEFAULT_RECIPIENT`

## Project Structure

```
notification-service/
├── app.py                      # Entry point — Flask /health + starts consumer thread
├── requirements.txt
├── Dockerfile
├── .env.example
├── src/
│   ├── consumer.py             # Kafka consumer loop (daemon thread)
│   ├── handlers.py             # Event → email routing
│   ├── mailer.py               # SMTP send logic (smtplib)
│   └── templates/              # Plain-text email body templates
│       ├── subscription_created.txt
│       ├── subscription_canceled.txt
│       ├── payment_succeeded.txt
│       └── payment_failed.txt
├── tests/
│   ├── test_handlers.py        # Handler dispatch + health endpoint tests
│   └── test_consumer.py        # Consumer message processing tests
├── k8s/                        # Production Kubernetes manifests
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── configmap.yaml
│   └── network-policy.yaml
└── k8s/local/                  # Local Docker Desktop manifests
    ├── deployment.yaml         # imagePullPolicy: Never
    ├── service.yaml
    ├── configmap.yaml
    ├── network-policy.yaml
    └── secret.yaml
```

## Kafka Events Consumed

| Topic | Event field | Action |
|---|---|---|
| `subscription.changed` | `subscription.created` | Send subscription confirmation email |
| `subscription.changed` | `subscription.canceled` | Send cancellation email |
| `payment.succeeded` | `payment.succeeded` | Send payment receipt email |
| `payment.failed` | `payment.failed` | Send payment failure alert email |

## Getting Started

### Requirements
- Python 3.12+
- A running Kafka broker
- A Mailtrap account (free) or any SMTP server

### Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Fill in your Kafka broker and Mailtrap SMTP credentials
```

### Run locally

```bash
flask run --host=0.0.0.0 --port=5000
```

### Tests

```bash
KAFKA_ENABLED=false pytest tests/ -v
```

### Lint

```bash
flake8 src/ app.py --max-line-length=120
```

## Local Kubernetes Deployment

```bash
# 1. Build the image
docker build -t notification-service:latest .

# 2. Load into Kubernetes containerd (Docker Desktop requirement)
docker save notification-service:latest | docker exec -i $(docker ps -qf "name=desktop-control-plane") ctr -n k8s.io images import -

# 3. Fill in your Mailtrap credentials
# Edit k8s/local/secret.yaml

# 4. Deploy
kubectl apply -f k8s/local/

# 5. Verify
kubectl get pods
kubectl logs -l app=notification-service
```

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `KAFKA_BROKERS` | Kafka broker address | `kafka:9092` |
| `KAFKA_ENABLED` | Set to `false` to disable consumer | `true` |
| `SMTP_HOST` | SMTP server host | `sandbox.smtp.mailtrap.io` |
| `SMTP_PORT` | SMTP server port | `2525` |
| `SMTP_USER` | SMTP username | — |
| `SMTP_PASS` | SMTP password | — |
| `MAIL_FROM` | Sender address shown in emails | `noreply@abonnement.local` |
| `DEFAULT_RECIPIENT` | Fallback email when not in event payload | `user@example.com` |

## GitHub Actions Secrets Required

| Secret | Description |
|---|---|
| `DOCKERHUB_USERNAME` / `DOCKERHUB_TOKEN` | DockerHub credentials |
| `SMTP_USER` | Mailtrap SMTP username |
| `SMTP_PASS` | Mailtrap SMTP password |
| `DEFAULT_RECIPIENT` | Fallback recipient email |
| `KUBECONFIG_LOCAL` | Local cluster kubeconfig (self-hosted runner) |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_REGION` | AWS credentials |
| `EKS_CLUSTER_NAME` | EKS cluster name |
| `AZURE_CREDENTIALS` | Azure service principal JSON |
| `AKS_CLUSTER_NAME` / `AKS_RESOURCE_GROUP` | AKS cluster info |
