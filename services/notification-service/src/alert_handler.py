import asyncio
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import httpx
from prometheus_client import Counter, Histogram

logger = logging.getLogger(__name__)

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_FROM = os.getenv("SMTP_FROM_ADDRESS")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
WEBHOOK_URL = os.getenv("NOTIFICATION_WEBHOOK_URL", "")
ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO", "admin@smart-irrigation.local")
THRESHOLD = os.getenv("ALERT_SEVERITY_THRESHOLD", "warning")

SEVERITY_ORDER = {"info": 0, "warning": 1, "critical": 2}
THRESHOLD_VALUE = SEVERITY_ORDER.get(THRESHOLD.lower(), 1)

ALERTS_RECEIVED = Counter(
    "notification_service_alerts_received_total",
    "Alerts received by the notification service",
    ["source", "severity"],
)
DELIVERIES = Counter(
    "notification_service_deliveries_total",
    "Notification delivery attempts by channel and status",
    ["channel", "status"],
)
WEBHOOK_LATENCY = Histogram(
    "notification_service_webhook_delivery_seconds",
    "Webhook delivery latency",
)


class AlertHandler:
    def __init__(self) -> None:
        self._thread_pool = ThreadPoolExecutor(max_workers=2)

    def shutdown(self) -> None:
        self._thread_pool.shutdown(wait=False, cancel_futures=True)

    def should_dispatch(self, severity: str) -> bool:
        return SEVERITY_ORDER.get(str(severity).lower(), 0) >= THRESHOLD_VALUE

    def _send_smtp_sync(self, subject: str, body: str) -> None:
        import smtplib
        from email.mime.text import MIMEText

        assert SMTP_HOST is not None
        assert SMTP_FROM is not None
        assert SMTP_PASSWORD is not None
        assert ALERT_EMAIL_TO is not None

        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = SMTP_FROM
        msg["To"] = ALERT_EMAIL_TO
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_FROM, SMTP_PASSWORD)
            server.send_message(msg)

    async def send_email(self, subject: str, body: str) -> None:
        if not all([SMTP_HOST, SMTP_FROM, SMTP_PASSWORD]):
            logger.debug("SMTP not configured, skipping email")
            DELIVERIES.labels("email", "skipped").inc()
            return
        try:
            await asyncio.get_running_loop().run_in_executor(
                self._thread_pool, self._send_smtp_sync, subject, body
            )
            logger.info("Email sent: %s", subject)
            DELIVERIES.labels("email", "success").inc()
        except Exception as exc:
            logger.error("Failed to send email: %s", exc)
            DELIVERIES.labels("email", "failed").inc()

    async def send_webhook(self, payload: dict[str, Any]) -> None:
        if not WEBHOOK_URL:
            DELIVERIES.labels("webhook", "skipped").inc()
            return
        try:
            with WEBHOOK_LATENCY.time():
                async with httpx.AsyncClient() as client:
                    response = await client.post(WEBHOOK_URL, json=payload, timeout=10)
                    response.raise_for_status()
            logger.info("Webhook delivered")
            DELIVERIES.labels("webhook", "success").inc()
        except Exception as exc:
            logger.error("Webhook failed: %s", exc)
            DELIVERIES.labels("webhook", "failed").inc()

    async def dispatch_alert(self, payload: dict[str, Any], source: str) -> dict[str, str]:
        severity = str(payload.get("severity", "warning")).lower()
        ALERTS_RECEIVED.labels(source, severity).inc()
        subject = f"[{severity.upper()}] Smart Irrigation Alert"
        body = json.dumps(payload, indent=2)
        await asyncio.gather(self.send_email(subject, body), self.send_webhook(payload))
        return {"status": "accepted", "source": source, "severity": severity}

    def normalize_alertmanager_alert(
        self,
        alert: dict[str, Any],
        payload_status: str,
    ) -> dict[str, Any]:
        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})
        return {
            "source": "alertmanager",
            "status": alert.get("status", payload_status),
            "severity": labels.get("severity", "warning"),
            "alertname": labels.get("alertname", "unknown"),
            "service": labels.get("job") or labels.get("service", "unknown"),
            "summary": annotations.get("summary", ""),
            "description": annotations.get("description", ""),
            "startsAt": alert.get("startsAt"),
            "endsAt": alert.get("endsAt"),
        }
