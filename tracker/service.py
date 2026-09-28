import asyncio
import logging
from sqlalchemy import select
from .db import Session, Product, PricePoint, Alert
from .sources import fetch_price

log = logging.getLogger(__name__)

async def check_product(product_id, fetcher=fetch_price):
    async with Session() as session:
        product = await session.get(Product, product_id)
        if product is None or not product.active: return None
        try:
            amount = await fetcher(product)
            if type(amount) is not int or not 0 <= amount <= 2_000_000_000:
                raise ValueError("Invalid source amount")
        except Exception as exc:
            # Do not store response URLs/headers, which may contain credentials.
            product.error = f"Price fetch failed ({type(exc).__name__})"
            await session.commit()
            return {"product_id": product_id, "error": product.error}
    async with Session.begin() as session:
        product = await session.scalar(select(Product).where(Product.id == product_id).with_for_update())
        if product is None or not product.active: return None
        point = PricePoint(product_id=product_id, amount=amount)
        session.add(point)
        await session.flush()
        below = amount < product.target
        if below and not product.below:
            session.add(Alert(product_id=product_id, point_id=point.id,
                message=f"{product.name}: {amount / 100:.2f} {product.currency}, below {product.target / 100:.2f}"))
        product.below = below
        product.error = None
        return {"product_id":product_id, "amount":amount, "point_id":point.id}

async def poll_all():
    async with Session() as session:
        ids = list(await session.scalars(select(Product.id).where(Product.active.is_(True))))
    semaphore = asyncio.Semaphore(4)
    async def run(pid):
        async with semaphore:
            try: return await check_product(pid)
            except Exception: log.exception("Product %s polling failed", pid); return {"product_id":pid,"error":"Database failure"}
    return await asyncio.gather(*(run(pid) for pid in ids))
