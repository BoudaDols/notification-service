import smtplib
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)


class Mailer:
    def __init__(self):
        self.host = os.environ.get("SMTP_HOST", "sandbox.smtp.mailtrap.io")
        self.port = int(os.environ.get("SMTP_PORT", "2525"))
        self.user = os.environ.get("SMTP_USER", "")
        self.password = os.environ.get("SMTP_PASS", "")
        self.mail_from = os.environ.get("MAIL_FROM", "noreply@abonnement.local")

    def send(self, to: str, subject: str, body: str) -> None:
        """Send a plain-text email via SMTP."""
        msg = MIMEMultipart()
        msg["From"] = self.mail_from
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        try:
            with smtplib.SMTP(self.host, self.port, timeout=10) as server:
                server.starttls()
                server.login(self.user, self.password)
                server.sendmail(self.mail_from, to, msg.as_string())
            logger.info(f"Email sent to {to} — subject: {subject}")
        except Exception as e:
            logger.error(f"Failed to send email to {to}: {e}")
            raise
