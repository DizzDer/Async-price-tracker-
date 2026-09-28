# Async Price Tracker

Working asynchronous price-monitoring service: FastAPI, SQLAlchemy, PostgreSQL or SQLite, Celery/Redis, Alembic and Docker Compose. Registers products, stores price history and creates an alert when a price first drops **strictly below** its threshold. Repeated low prices do not spam alerts; returning to or above the threshold rearms the alert.

## Run locally (no Docker needed)

Python 3.11+:

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
uvicorn tracker.api:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000/docs. Register with `POST /products`:

```json
{"name":"Demo coffee","url":"demo://coffee","target":"20.00","currency":"USD"}
```

Call `POST /products/1/check`, then `GET /products/1/history` and `GET /alerts`. The demo returns 19.95 by default and needs no external service. `DEMO_PRICE` configures its value. `python -m tracker` polls all active products once; local mode does not start a hidden scheduler.

Prices returned by the API are integer minor units: 1995 means 19.95. Input accepts decimal strings with up to two fractional digits. Currency is a user-declared three-letter label; automatic currency detection/conversion and currencies with other decimal scales are not supported. DELETE deactivates monitoring while preserving history. List endpoints have bounded pagination/limits.

## Docker stack

Copy `.env.example` to `.env`, replace both password placeholders with distinct random values (use URL-safe alphanumeric characters for the database password), then:

```sh
docker compose up --build
```

Postgres and Redis stay on the internal Compose network. The API is exposed only at 127.0.0.1:8000. A migration job completes before API/worker startup. Beat schedules a batch every five minutes; a Redis lease prevents overlapping worker batches. Set `X-API-Key` to the configured key on API requests. Swagger requests can supply it as the header parameter.

Keep only one Beat instance. SQLite local mode is intended for serial single-user checks; use PostgreSQL for concurrent use. `AUTO_CREATE_DB=0` selects migration-managed schema. Manually: `alembic upgrade head`.

## Real product pages

Set `ALLOWED_HOSTS` to a comma-separated list of **trusted shop domains you administer/approve**. Register an HTTPS URL and a CSS `selector`; the default reads `<meta property="product:price:amount" content="19.95">`. Text-only price nodes must contain a plain decimal without symbols/thousands separators. Fetches use a 15-second timeout, a 1 MB decompressed limit, no redirects and no proxy environment. Private/reserved DNS results are rejected.

This is not a universal scraper: JavaScript-rendered prices, login pages, CAPTCHAs, currency inference and changing merchant markup require a dedicated adapter. Respect each site's usage terms and rate limits. Domain allowlisting is administrator configuration, not an API field. Deploy behind network egress controls: the transport resolves DNS separately from validation, so validation alone is not a complete DNS-rebinding defense. Do not expose this local demo directly to the internet.

## Alerts and optional delivery

All alerts are persisted in the API inbox. No external messages are sent by default. The Celery worker can deliver pending alerts when explicitly configured:

- Telegram: `ALERT_CHANNEL=telegram`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.
- Email over implicit TLS: `ALERT_CHANNEL=email`, `SMTP_HOST`, optional `SMTP_PORT` (465), `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_TO`.

Pass these environment variables to the worker (Compose does not automatically forward arbitrary host variables). Keep credentials out of Git. Failed deliveries retain a pending record and retry next batch. Delivery is at least once: a crash after sending but before committing can cause a duplicate. Provider integrations have mock-based tests; no real message is sent by the test suite.

## Tests and current validation

```sh
pip install -r requirements-dev.txt
python -m pytest -q
```

Tests cover API authorization, duplicates, input limits, exact cents, threshold crossings/rearming, history, failure recovery, source parsing, migration upgrade/downgrade and notification retry. SQLite tests run locally; PostgreSQL/Redis/Docker integration has its own CI job. Real retailer pages and external delivery need testing with your chosen providers. This is a functional first release, not a claim of production certification.

Documentation: [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/), [SQLAlchemy asyncio](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html), [Celery periodic tasks](https://docs.celeryq.dev/en/stable/userguide/periodic-tasks.html).
