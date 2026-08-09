"""Notification domain model + tiny SQLAlchemy-like row mirror.

We don't pull in a full ORM dependency for the worker — the row is
materialised from the queue payload (a dict) and only written back to
Postgres for audit. Keeping it a plain dataclass makes the worker
trivial to test in isolation.
"""
from __future__ import annotations

import enum
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional


class NotificationStatus(str, enum.Enum):
    QUEUED = "queued"
    SENT = "sent"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class Notification:
    id: str
    to_address: str
    subject: str
    body: str
    template_id: Optional[str] = None
    status: NotificationStatus = NotificationStatus.QUEUED
    attempts: int = 0
    last_error: Optional[str] = None
    created_at: float = field(default_factory=time.time)

    @classmethod
    def from_payload(cls, payload: Dict[str, Any]) -> "Notification":
        return cls(
            id=payload["id"],
            to_address=payload["to_address"],
            subject=payload["subject"],
            body=payload["body"],
            template_id=payload.get("template_id"),
        )

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d
