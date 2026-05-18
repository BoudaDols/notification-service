import logging
import os
from flask import Flask, jsonify
from src.consumer import start_consumer_thread

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ── Flask app ─────────────────────────────────────────────────────────────────
app = Flask(__name__)


@app.route("/health")
def health():
    """Liveness/readiness probe for Kubernetes."""
    return jsonify({"status": "ok"}), 200


# ── Start Kafka consumer thread on boot ───────────────────────────────────────
if os.environ.get("KAFKA_ENABLED", "true") == "true":
    start_consumer_thread()
    logger.info("Kafka consumer thread started")
else:
    logger.info("Kafka disabled (KAFKA_ENABLED=false) — consumer not started")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
