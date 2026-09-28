import os
import secrets
from contextlib import asynccontextmanager
from typing import Annotated
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from .db import Session, Product, PricePoint, Alert, init_db
from .sources import cents, validate_url
from .service import check_product

async def authorize(x_api_key: Annotated[str | None, Header()] = None):
    expected = os.getenv("API_KEY")
    if expected and not secrets.compare_digest(x_api_key or "", expected):
        raise HTTPException(401, "Invalid API key")

@asynccontextmanager
async def lifespan(app):
    if os.getenv("AUTO_CREATE_DB", "1") == "1": await init_db()
    yield

app = FastAPI(title="Async Price Tracker", version="1.0.0", lifespan=lifespan,
              dependencies=[Depends(authorize)])

class ProductInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    url: str = Field(max_length=2048)
    selector: str = Field(default='meta[property="product:price:amount"]', min_length=1, max_length=200)
    currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$")
    target: str
    @field_validator("url")
    @classmethod
    def valid_url(cls, value): validate_url(value); return value
    @field_validator("target")
    @classmethod
    def valid_target(cls, value): cents(value); return value
    @field_validator("name")
    @classmethod
    def valid_name(cls, value):
        if not value.strip(): raise ValueError("Name is required")
        return value.strip()
    @field_validator("selector")
    @classmethod
    def valid_selector(cls, value):
        import soupsieve
        try: soupsieve.compile(value)
        except Exception as exc: raise ValueError("Invalid CSS selector") from exc
        return value

@app.get("/health")
async def health(): return {"status":"ok"}

@app.post("/products", status_code=201)
async def create_product(data: ProductInput):
    async with Session() as session:
        product = Product(**data.model_dump(exclude={"target"}), target=cents(data.target))
        session.add(product)
        try: await session.commit()
        except IntegrityError as exc: raise HTTPException(409, "URL already registered") from exc
        return {"id":product.id}

@app.get("/products")
async def products(limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    async with Session() as session:
        return list(await session.scalars(select(Product).order_by(Product.id).offset(offset).limit(limit)))

@app.post("/products/{product_id}/check")
async def check(product_id: int):
    result = await check_product(product_id)
    if result is None: raise HTTPException(404, "Active product not found")
    if "error" in result: raise HTTPException(502, result["error"])
    return result

@app.delete("/products/{product_id}", status_code=204)
async def deactivate(product_id: int):
    async with Session.begin() as session:
        product = await session.get(Product, product_id)
        if product is None: raise HTTPException(404, "Product not found")
        product.active = False

@app.get("/products/{product_id}/history")
async def history(product_id: int, limit: int = Query(100, ge=1, le=500)):
    async with Session() as session:
        if await session.get(Product, product_id) is None: raise HTTPException(404, "Product not found")
        return list(await session.scalars(select(PricePoint).where(PricePoint.product_id == product_id).order_by(PricePoint.id.desc()).limit(limit)))

@app.get("/alerts")
async def alerts(limit: int = Query(100, ge=1, le=500)):
    async with Session() as session:
        return list(await session.scalars(select(Alert).order_by(Alert.id.desc()).limit(limit)))
