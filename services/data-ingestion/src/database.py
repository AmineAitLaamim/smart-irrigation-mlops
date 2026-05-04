import os
import asyncio
import asyncpg
from typing import AsyncGenerator, Optional
from dataclasses import dataclass, field
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://irrigation_user:changeme@timescaledb:5432/irrigation_db")
DB_POOL_MIN_SIZE = int(os.getenv("DB_POOL_MIN_SIZE", "2"))
DB_POOL_MAX_SIZE = int(os.getenv("DB_POOL_MAX_SIZE", "10"))


@dataclass
class IngestionStats:
    total_processed: int = 0
    valid_readings: int = 0
    anomalies_flagged: int = 0
    last_processed_at: Optional[datetime] = None
    errors: int = 0
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def increment(self, processed: bool = False, valid: bool = False, anomaly: bool = False, error: bool = False):
        async with self._lock:
            if processed:
                self.total_processed += 1
            if valid:
                self.valid_readings += 1
            if anomaly:
                self.anomalies_flagged += 1
            if error:
                self.errors += 1
            self.last_processed_at = datetime.utcnow()

    def to_dict(self):
        return {
            "total_processed": self.total_processed,
            "valid_readings": self.valid_readings,
            "anomalies_flagged": self.anomalies_flagged,
            "last_processed_at": self.last_processed_at.isoformat() if self.last_processed_at else None,
            "errors": self.errors
        }


stats = IngestionStats()


class Database:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

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

    async def fetchrow(self, query: str, *args):
        if not self.pool:
            raise RuntimeError("Database pool not initialized. Call connect() first.")
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetch(self, query: str, *args):
        if not self.pool:
            raise RuntimeError("Database pool not initialized. Call connect() first.")
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def execute(self, query: str, *args):
        if not self.pool:
            raise RuntimeError("Database pool not initialized. Call connect() first.")
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)


db = Database()


async def get_db_conn() -> AsyncGenerator[asyncpg.Connection, None]:
    if not db.pool:
        raise RuntimeError("Database pool not initialized. Call connect() first.")
    async with db.pool.acquire() as connection:
        yield connection