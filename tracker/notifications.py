"""Optional delivery; credentials are read only by the worker process."""
import asyncio
import os
import smtplib
import ssl
from email.message import EmailMessage
import httpx
from sqlalchemy import select
from .db import Session, Alert

async def send(message):
    channel = os.getenv("ALERT_CHANNEL", "inbox")
    if channel == "telegram":
        token, chat = os.environ["TELEGRAM_BOT_TOKEN"], os.environ["TELEGRAM_CHAT_ID"]
        async with httpx.AsyncClient(timeout=15, trust_env=False) as client:
            response = await client.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id":chat,"text":message})
            response.raise_for_status()
            if response.json().get("ok") is not True: raise RuntimeError("Telegram rejected delivery")
    elif channel == "email":
        def deliver():
            mail = EmailMessage()
            mail["Subject"] = "Price alert"
            mail["From"] = os.environ["SMTP_FROM"]
            mail["To"] = os.environ["SMTP_TO"]
            mail.set_content(message)
            with smtplib.SMTP_SSL(os.environ["SMTP_HOST"], int(os.getenv("SMTP_PORT","465")), timeout=15, context=ssl.create_default_context()) as smtp:
                smtp.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
                smtp.send_message(mail)
        await asyncio.to_thread(deliver)
    else:
        raise ValueError("Configure ALERT_CHANNEL as telegram or email")

async def dispatch(sender=send):
    if sender is send and os.getenv("ALERT_CHANNEL", "inbox") == "inbox": return 0
    delivered = 0
    async with Session() as session:
        pending = list(await session.scalars(select(Alert).where(Alert.delivered.is_(False)).order_by(Alert.id).limit(100)))
        for alert in pending:
            try:
                await sender(alert.message)
                alert.delivered = True
                alert.delivery_error = None
                delivered += 1
            except Exception as exc:
                alert.delivery_error = type(exc).__name__
            await session.commit()
    return delivered
