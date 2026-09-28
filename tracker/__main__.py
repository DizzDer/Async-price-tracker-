import asyncio
from .db import init_db
from .service import poll_all
async def main():
    await init_db()
    print(await poll_all())
asyncio.run(main())
