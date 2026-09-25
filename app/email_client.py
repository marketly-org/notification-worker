"""Thin wrapper around smtplib.SMTP for sending transactional email.

Kept as a separate module so the Celery task can be unit-tested by
injecting a fake client (see tests/test_tasks.py).
"""
from __future__ import annotations

import smtplib
import os
from email.message import EmailMessage

from .config import settings


class EmailClient:
    """Synchronous SMTP client. One connection per send (transactional
    volume is low; a connection pool would be over-engineering)."""

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        username: str | None = None,
        password: str | None = None,
        use_tls: bool | None = None,
        timeout: float | None = None,
        from_address: str | None = None,
    ) -> None:
        # Resolve configuration at runtime, respecting environment variables.
        # Resolve configuration using the settings object, which already incorporates
        # environment variables via pydantic/BaseSettings. This avoids issues where
        # os.getenv may not reflect the intended values at import time.
        self.host = host if host is not None else settings.smtp_host
        self.port = port if port is not None else int(settings.smtp_port)
        self.username = username if username is not None else settings.smtp_username
        self.password = password if password is not None else settings.smtp_password
        self.use_tls = (
            use_tls
            if use_tls is not None
            else str(settings.smtp_use_tls).lower() == "true"
        )
        self.timeout = timeout if timeout is not None else float(settings.smtp_timeout_s)
        self.from_address = from_address if from_address is not None else settings.from_address

    def send(self, to: str, subject: str, body: str, reply_to: str | None = None) -> None:
        msg = EmailMessage()
        msg["From"] = self.from_address
        msg["To"] = to
        msg["Subject"] = subject
        if reply_to:
            msg["Reply-To"] = reply_to
        msg.set_content(body)

        with smtplib.SMTP(self.host, self.port, timeout=self.timeout) as smtp:
            if self.use_tls:
                smtp.starttls()
            if self.username and self.password:
                smtp.login(self.username, self.password)
            smtp.send_message(msg)

# Module-level singleton used by the Celery task. Tests monkey-patch
# this attribute to inject a fake client.
default_client = EmailClient()
