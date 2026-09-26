"""Thin wrapper around smtplib.SMTP for sending transactional email.

Kept as a separate module so the Celery task can be unit-tested by
injecting a fake client (see tests/test_tasks.py).
"""
from __future__ import annotations

import smtplib
import time
from email.message import EmailMessage

from .config import settings


class EmailClient:
    """Synchronous SMTP client. One connection per send (transactional
    volume is low; a connection pool would be over-engineering)."""

    def __init__(
        self,
        host: str = settings.smtp_host,
        port: int = settings.smtp_port,
        username: str = settings.smtp_username,
        password: str = settings.smtp_password,
        use_tls: bool = settings.smtp_use_tls,
        timeout: float = settings.smtp_timeout_s,
        from_address: str = settings.from_address,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.timeout = timeout
        self.from_address = from_address

    def send(self, to: str, subject: str, body: str, reply_to: str | None = None) -> None:
        """Send an email with retry and exponential backoff for transient SMTP errors."""
        max_attempts = 3
        delay = 1.0  # initial backoff in seconds

        for attempt in range(1, max_attempts + 1):
            msg = EmailMessage()
            msg["From"] = self.from_address
            msg["To"] = to
            msg["Subject"] = subject
            if reply_to:
                msg["Reply-To"] = reply_to
            msg.set_content(body)

            try:
                with smtplib.SMTP(self.host, self.port, timeout=self.timeout) as smtp:
                    if self.use_tls:
                        smtp.starttls()
                    if self.username and self.password:
                        smtp.login(self.username, self.password)
                    smtp.send_message(msg)
                # Success, exit the retry loop
                return
            except Exception as exc:
                exc_name = type(exc).__name__
                # If the exception is not considered retryable, re-raise immediately
                if exc_name not in settings.retryable_smtp_errors:
                    raise
                # If this was the last attempt, re-raise the exception
                if attempt == max_attempts:
                    raise
                # Otherwise, wait for backoff period and retry
                time.sleep(delay)
                delay *= 2  # exponential backoff

# Module-level singleton used by the Celery task. Tests monkey-patch
# this attribute to inject a fake client.
default_client = EmailClient()
