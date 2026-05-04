import os
import asyncpg
from typing import AsyncGenerator

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://irrigation_user:changeme@timescaledb:5432/irrigation_db")
DB_POOL_MIN_SIZE = int(os.getenv("DB_POOL_MIN_SIZE", "2"))
DB_POOL_MAX_SIZE = int(os.getenv("DB_POOL_MAX_SIZE", "10"))

class Database:
    def __init__(self):
        self.pool: asyncpg.Pool = None

    async def connect(self):
        if not self.pool:
            self.pool = await asyncpg.create_pool(
                dsn=DATABASE_URL,
                min_size=DB_POOL_MIN_SIZE,
                max_size=DB_POOL_MAX_SIZE
            )

    async def disconnect(self):
        if self.pool:
            await self.pool.close()
            self.pool = None

db = Database()

async def get_db_conn() -> AsyncGenerator[asyncpg.Connection, None]:
    async with db.pool.acquire() as connection:
        yield connection
