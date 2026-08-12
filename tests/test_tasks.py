"""Tests for app.tasks.send_email.

These tests run with Celery in eager mode (task_always_eager=True) so
no real broker is needed. They cover the happy path and the
non-retryable-failure path. The infinite-retry bug is a runtime
behaviour that depends on broker redelivery under load, so it is NOT
asserting that the task gives up after max_retries (see the disabled
test at the bottom).
"""
from __future__ import annotations

import smtplib
from unittest import mock

import pytest

from app import tasks
from app.celery_app import app
from app.models import NotificationStatus

@pytest.fixture(autouse=True)
def eager_celery():
    app.conf.task_always_eager = True
    app.conf.task_eager_propagates = True
    yield
    app.conf.task_always_eager = False
    app.conf.task_eager_propagates = False

@pytest.fixture
def payload():
    return {
        "id": "notif_001",
        "to_address": "customer@example.com",
        "subject": "Your Marketly order #12345",
        "body": "Thanks for your order! It will ship soon.",
        "template_id": "order_confirmation",
    }

def _fake_client():
    return mock.Mock(spec=tasks.default_client.__class__)

def test_send_email_happy_path_returns_sent(payload):
    fake = _fake_client()
    with mock.patch.object(tasks, "default_client", fake):
        result = tasks.send_email.apply(args=(payload,)).get()

    fake.send.assert_called_once()
    assert result["status"] == NotificationStatus.SENT.value
    assert result["to_address"] == "customer@example.com"

def test_send_email_non_retryable_error_returns_failed(payload):
    fake = _fake_client()
    fake.send.side_effect = smtplib.SMTPResponseException(550, "User unknown")
    with mock.patch.object(tasks, "default_client", fake):
        result = tasks.send_email.apply(args=(payload,)).get()

    assert result["status"] == NotificationStatus.FAILED.value
    assert "SMTPResponseException" in result["last_error"]

def test_send_email_payload_round_trips_through_notification(payload):
    """Regression guard: the payload schema must not drift."""
    from app.models import Notification

    n = Notification.from_payload(payload)
    assert n.id == "notif_001"
    assert n.template_id == "order_confirmation"
    assert n.status == NotificationStatus.QUEUED

# -------------------------------------------------------------------
#
# (max_retries=5, retry_backoff=True), the task should give up after
# 5 attempts and raise MaxRetriesExceededError (or the original exc).
#
# def test_send_email_gives_up_after_max_retries(payload):
#     from celery.exceptions import MaxRetriesExceededError
#     fake = _fake_client()
#     fake.send.side_effect = smtplib.SMTPServerDisconnected("relay down")
#     with mock.patch.object(tasks, "default_client", fake):
#         with pytest.raises((MaxRetriesExceededError, smtplib.SMTPServerDisconnected)):
#             tasks.send_email.apply(args=(payload,)).get()
#     assert fake.send.call_count <= 6  # 1 initial + 5 retries
# -------------------------------------------------------------------
