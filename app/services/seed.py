from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.catalog import PRODUCTS
from app.models import Product


async def seed_products(session: AsyncSession) -> None:
    existing = set((await session.execute(select(Product.sku))).scalars().all())
    for p in PRODUCTS:
        if p["sku"] in existing:
            continue
        session.add(
            Product(
                sku=p["sku"],
                slug=p["slug"],
                name_ar=p["name_ar"],
                ritual_slot=p["ritual_slot"],
                active=True,
            )
        )
    await session.commit()
