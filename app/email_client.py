"""Thin wrapper around smtplib.SMTP for sending transactional email.

Kept as a separate module so the Celery task can be unit-tested by
injecting a fake client (see tests/test_tasks.py).
"""
from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Optional

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

    def send(self, to: str, subject: str, body: str, reply_to: Optional[str] = None) -> None:
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
