"""Celery application instance + broker/backend configuration."""
from __future__ import annotations

from celery import Celery
from celery.signals import worker_ready, worker_shutdown

from .config import settings

app = Celery(
    "notification-worker",
    broker=settings.celery_broker,
    backend=settings.celery_backend,
    include=["app.tasks"],
)

app.conf.update(
    # Serialize with JSON — payloads are plain dicts, no need for pickle.
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Reliability knobs.
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    broker_connection_retry_on_startup=True,
    # Worker
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=200,
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Default task policy — individual tasks can override.
    task_default_queue="notifications",
    task_routes={
        "app.tasks.send_email": {"queue": "notifications"},
    },
)


@worker_ready.connect
def _start_health_server(**_kwargs) -> None:
    # Imported lazily so the test suite (which doesn't start a worker)
    # doesn't try to bind a port on import.
    from . import health

    health.start()


@worker_shutdown.connect
def _stop_health_server(**_kwargs) -> None:
    from . import health

    health.stop()


__all__ = ["app"]
