import asyncio
import os
from celery import Celery
from redis import Redis
from .service import poll_all
from .notifications import dispatch

broker = os.getenv("REDIS_URL", "redis://localhost:6379/0")
app = Celery("tracker", broker=broker)
app.conf.update(broker_connection_retry_on_startup=True,
    beat_schedule={"poll-prices":{"task":"tracker.poll","schedule":300.0}},
    task_serializer="json", accept_content=["json"], timezone="UTC")

@app.task(name="tracker.poll", soft_time_limit=240, time_limit=270)
def poll():
    # Single fleet-wide polling batch; manual API checks should not overlap in SQLite mode.
    with Redis.from_url(broker).lock("tracker:poll", timeout=285, blocking_timeout=0) as lock:
        return asyncio.run(batch())

async def batch():
    results = await poll_all()
    await dispatch()
    return results
