# notification-worker

Email notification worker for the **Marketly** e-commerce platform.

Consumes notification payloads from the `notifications` Celery queue
and sends transactional email via SMTP. Retries transient SMTP errors
(server disconnected, timeout, connection reset) and fails hard on
non-retryable errors (550 user unknown, malformed address).

## Stack

- **Python 3.12** + **Celery 5.4**
- Redis (broker + result backend), SMTP relay

## Queues

| Queue | Task | Description |
|-------|------|-------------|
| `notifications` | `app.tasks.send_email` | Send one transactional email |

## Local development

```bash
pip install -r requirements.txt
celery -A app.celery_app worker --loglevel=info -Q notifications
```

## Tests

```bash
pip install -r requirements.txt
pytest tests/ -v
ruff check app/ tests/
```

## Configuration

| Env var | Default | Description |
|---------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379/0` | Broker + result backend |
| `SMTP_HOST` | `localhost` | SMTP relay host |
| `SMTP_PORT` | `2525` | SMTP relay port |
| `SMTP_USE_TLS` | `true` | Issue STARTTLS before login |
| `SMTP_TIMEOUT_S` | `5.0` | Per-send SMTP timeout |
| `HEALTH_PORT` | `8080` | HTTP health server port |
