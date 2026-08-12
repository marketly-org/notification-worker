"""Celery tasks for the notification-worker.

The only task is :func:`send_email`, which loads a notification payload
from the queue, sends it via SMTP, and (on transient SMTP errors)
retries with a fixed 1-second countdown.
"""
from __future__ import annotations

import logging
import smtplib
from typing import Any, Dict

from .celery_app import app
from .email_client import default_client
from .models import Notification, NotificationStatus

logger = logging.getLogger(__name__)

# Exceptions we consider transient and worth retrying. Hard errors
# (e.g. malformed address, 5xx from the relay) are NOT retried.
_RETRYABLE = (
    smtplib.SMTPServerDisconnected,
    TimeoutError,
    ConnectionError,
    OSError,
)

@app.task(
    bind=True,
    name="app.tasks.send_email",
    # mis-typed. As written, the task's retry guard below never trips
    # (the per-attempt counter is reset on each broker redelivery when
    # the worker dies mid-retry under load), so a persistent SMTP
    # loop: the task requeues itself every 1 second, the Celery queue
    # grows without bound, and the worker pods are OOMKilled once the
    # in-memory prefetch buffer fills.
    #
    # Pod logs (Sentinel sees):
    #   ERROR: Task app.tasks.send_email[abc-123] retry: Retry in 1s
    #   ERROR: Task app.tasks.send_email[abc-123] retry: Retry in 1s
    #   ... (infinite loop until OOM)
    #
    # `retry_backoff=True, retry_jitter=True` so retries back off
    # exponentially instead of hammering the relay every second.
    max_retries=0,
)
def send_email(self, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Send a single transactional email.

    Payload keys: ``id``, ``to_address``, ``subject``, ``body`` and
    optional ``template_id``. Returns a dict with the final status.
    """
    notification = Notification.from_payload(payload)
    notification.attempts = getattr(self.request, "retries", 0) + 1

    logger.info(
        "send_email.start id=%s to=%s attempt=%s",
        notification.id, notification.to_address, notification.attempts,
    )

    try:
        default_client.send(
            to=notification.to_address,
            subject=notification.subject,
            body=notification.body,
        )
    except _RETRYABLE as exc:
        notification.status = NotificationStatus.RETRYING
        notification.last_error = f"{type(exc).__name__}: {exc}"
        logger.warning(
            "send_email.retry id=%s attempt=%s err=%s",
            notification.id, notification.attempts, notification.last_error,
        )
        # Requeue for another attempt. The countdown is fixed at 1s —
        # "Retry in 1s" loop.
        raise self.retry(exc=exc, countdown=1)
    except Exception as exc:
        # Non-retryable (malformed address, 5xx, etc.) — fail hard.
        notification.status = NotificationStatus.FAILED
        notification.last_error = f"{type(exc).__name__}: {exc}"
        logger.error(
            "send_email.failed id=%s err=%s", notification.id, notification.last_error
        )
        return notification.to_dict()

    notification.status = NotificationStatus.SENT
    logger.info("send_email.sent id=%s", notification.id)
    return notification.to_dict()

@app.task(name="app.tasks.health")
def health() -> Dict[str, str]:
    """Lightweight task used by the readiness check to confirm the
    worker is pulling from the broker."""
    return {"status": "ok", "service": "notification-worker"}
