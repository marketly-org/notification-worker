"""Environment-driven configuration for the notification-worker."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List

def _split_csv(v: str) -> List[str]:
    return [x.strip() for x in v.split(",") if x.strip()]

@dataclass(frozen=True)
class Settings:
    # Celery / Redis
    redis_url: str = field(
        default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379/0")
    )
    celery_broker: str = field(
        default_factory=lambda: os.getenv("CELERY_BROKER_URL", os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    )
    celery_backend: str = field(
        default_factory=lambda: os.getenv("CELERY_RESULT_BACKEND", os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    )

    # SMTP
    smtp_host: str = field(default_factory=lambda: os.getenv("SMTP_HOST", "localhost"))
    smtp_port: int = field(default_factory=lambda: int(os.getenv("SMTP_PORT", "2525")))
    smtp_username: str = field(default_factory=lambda: os.getenv("SMTP_USERNAME", ""))
    smtp_password: str = field(default_factory=lambda: os.getenv("SMTP_PASSWORD", ""))
    smtp_use_tls: bool = field(default_factory=lambda: os.getenv("SMTP_USE_TLS", "true").lower() == "true")
    smtp_timeout_s: float = field(default_factory=lambda: float(os.getenv("SMTP_TIMEOUT_S", "5.0")))

    # From / Reply-To
    from_address: str = field(
        default_factory=lambda: os.getenv("FROM_ADDRESS", "Marketly <no-reply@marketly.com>")
    )

    # Database (for the notification log)
    database_url: str = field(
        default_factory=lambda: os.getenv("DATABASE_URL", "postgresql://marketly:marketly@localhost:5432/marketly_notifications")
    )

    # Which exception types should trigger a retry. Anything else is a
    # hard failure (rejected, no retry).
    retryable_smtp_errors: tuple = ("TimeoutError", "ConnectionError", "SMTPServerDisconnected", "SMTPTimeoutError")

    @property
    def broker(self) -> str:
        return self.celery_broker

settings = Settings()
