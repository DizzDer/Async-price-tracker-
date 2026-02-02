<div align="center">

# Async Price Tracker 

Production-grade asynchronous price tracker with alerting & price history.  
**FastAPI + Celery + PostgreSQL + Redis + Docker + CI**

![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-API-success)
![Postgres](https://img.shields.io/badge/PostgreSQL-16-blue)
![Redis](https://img.shields.io/badge/Redis-7-red)
![License](https://img.shields.io/badge/License-MIT-green)

</div>

## Features
-  **FastAPI** REST API (+ Swagger / OpenAPI)
-  **Async PostgreSQL** (SQLAlchemy 2.0 async)
-  **Alembic** migrations
-  **Celery + Redis** background jobs (polling + alerts)
-  Price history per product
-  Alerts when price drops below threshold (Telegram/Email ready)
-  Docker Compose local stack
-  Tests + CI workflow

---

##  How it works
1. You register a product URL in the API.
2. Background job fetches the price on schedule.
3. New price point is stored in Postgres.
4. Alert rules are checked and notifications are sent.

---

## 🚀 Quickstart (Docker)
```bash
docker compose up --build
