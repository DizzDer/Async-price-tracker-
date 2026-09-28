import asyncio
import ipaddress
import os
import re
import socket
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit
import httpx
from bs4 import BeautifulSoup

DEMO_URL = "demo://coffee"

def cents(value):
    try:
        text = str(value).strip()
        if not re.fullmatch(r"[0-9]+(?:\.[0-9]{1,2})?", text):
            raise ValueError("Use a nonnegative decimal price, e.g. 19.95")
        result = int(Decimal(text) * 100)
        if result > 2_000_000_000: raise ValueError("Price too large")
        return result
    except InvalidOperation as exc:
        raise ValueError("Invalid price") from exc

def validate_url(url):
    if url == DEMO_URL: return
    parsed = urlsplit(url)
    allowed = {h.strip().lower() for h in os.getenv("ALLOWED_HOSTS", "").split(",") if h.strip()}
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port not in (None, 443) or parsed.fragment or parsed.hostname not in allowed:
        raise ValueError("Only HTTPS URLs on explicitly configured ALLOWED_HOSTS are supported")

async def fetch_price(product):
    validate_url(product.url)
    if product.url == DEMO_URL:
        return cents(os.getenv("DEMO_PRICE", "19.95"))
    host = urlsplit(product.url).hostname
    records = await asyncio.get_running_loop().getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    if not records or any(not ipaddress.ip_address(r[4][0]).is_global for r in records):
        raise ValueError("Private/reserved network destinations are forbidden")
    # Only administrator-selected trusted domains. Enforce network egress controls
    # when deploying: DNS resolution by the HTTP transport is a separate operation.
    async with httpx.AsyncClient(timeout=15, follow_redirects=False, trust_env=False) as client:
        async with client.stream("GET", product.url, headers={"User-Agent":"AsyncPriceTracker/1.0"}) as response:
            response.raise_for_status()
            if response.status_code != 200: raise ValueError("Expected HTTP 200; redirects are not followed")
            if "html" not in response.headers.get("content-type", "").lower(): raise ValueError("Expected HTML")
            body = bytearray()
            async for chunk in response.aiter_bytes():
                body.extend(chunk)
                if len(body) > 1_000_000: raise ValueError("Page exceeds 1 MB limit")
    return parse_html(bytes(body), product.selector)

def parse_html(body, selector):
    node = BeautifulSoup(body, "html.parser").select_one(selector)
    if node is None: raise ValueError("Price selector did not match")
    return cents(node.get("content", node.get_text(strip=True)))
