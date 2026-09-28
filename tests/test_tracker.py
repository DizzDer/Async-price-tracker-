import asyncio
import importlib
import os
import subprocess
import sys
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from tracker.sources import cents, parse_html, validate_url

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///" + str(tmp_path / "test.db"))
    monkeypatch.setenv("API_KEY", "test-key")
    monkeypatch.setenv("AUTO_CREATE_DB", "1")
    from tracker import db, service, api
    importlib.reload(db); importlib.reload(service); importlib.reload(api)
    with TestClient(api.app, headers={"X-API-Key":"test-key"}) as client: yield client

def product(client):
    response=client.post("/products",json={"name":"Coffee", "url":"demo://coffee", "target":"20.00"})
    assert response.status_code==201
    return response.json()["id"]

def test_lifecycle_and_crossing_alert(client, monkeypatch):
    pid=product(client)
    monkeypatch.setenv("DEMO_PRICE","19.95")
    for _ in range(2): assert client.post(f"/products/{pid}/check").status_code==200
    assert len(client.get("/alerts").json())==1
    assert len(client.get(f"/products/{pid}/history").json())==2
    monkeypatch.setenv("DEMO_PRICE","20.00")
    client.post(f"/products/{pid}/check")
    monkeypatch.setenv("DEMO_PRICE","19.00")
    client.post(f"/products/{pid}/check")
    assert len(client.get("/alerts").json())==2
    assert client.delete(f"/products/{pid}").status_code==204
    assert client.post(f"/products/{pid}/check").status_code==404
    assert len(client.get(f"/products/{pid}/history").json())==4

def test_validation_duplicate_and_auth(client):
    product(client)
    assert client.post("/products",json={"name":"Coffee","url":"demo://coffee","target":"2"}).status_code==409
    assert client.get("/products",headers={"X-API-Key":"wrong"}).status_code==401
    for target in ["NaN","-1","1.001","$12","1,200"]:
        assert client.post("/products",json={"name":"x","url":"demo://coffee","target":target}).status_code==422
    assert client.get("/products/999/history").status_code==404
    assert client.get("/products?limit=0").status_code==422

def test_fetch_failure_preserves_history(client, monkeypatch):
    pid=product(client)
    monkeypatch.setenv("DEMO_PRICE","NaN")
    assert client.post(f"/products/{pid}/check").status_code==502
    assert client.get(f"/products/{pid}/history").json()==[]
    monkeypatch.setenv("DEMO_PRICE","1.23")
    assert client.post(f"/products/{pid}/check").json()["amount"]==123
    assert client.get("/products").json()[0]["error"] is None

def test_html_and_money(monkeypatch):
    assert cents("0.29")==29
    assert parse_html(b'<meta property="product:price:amount" content="42.19">','meta[property="product:price:amount"]')==4219
    with pytest.raises(ValueError): parse_html(b'<p>none</p>', '.price')
    monkeypatch.setenv("ALLOWED_HOSTS","shop.example")
    validate_url("https://shop.example/item")
    for url in ["http://shop.example/", "https://evil.example/", "https://user:pass@shop.example/", "file:///etc/passwd"]:
        with pytest.raises(ValueError): validate_url(url)

def test_migration_roundtrip(tmp_path):
    env={**os.environ,"DATABASE_URL":"sqlite+aiosqlite:///"+str(tmp_path/'migrate.db')}
    for revision in ["head","head","base","head"]:
        command="downgrade" if revision=="base" else "upgrade"
        subprocess.run([sys.executable,"-m","alembic",command,revision],env=env,check=True,capture_output=True)


def test_alert_outbox_retry(client, monkeypatch):
    pid=product(client)
    monkeypatch.setenv("DEMO_PRICE","1.00")
    client.post(f"/products/{pid}/check")
    from tracker import notifications
    importlib.reload(notifications)
    async def fail(message): raise RuntimeError("secret provider detail")
    assert asyncio.run(notifications.dispatch(fail))==0
    assert client.get("/alerts").json()[0]["delivery_error"]=="RuntimeError"
    sent=[]
    async def succeed(message): sent.append(message)
    assert asyncio.run(notifications.dispatch(succeed))==1
    assert asyncio.run(notifications.dispatch(succeed))==0
    assert len(sent)==1
