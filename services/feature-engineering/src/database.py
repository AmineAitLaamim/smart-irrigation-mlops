import os
import asyncio
import asyncpg
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://irrigation_user:changeme@timescaledb:5432/irrigation_db")
DB_POOL_MIN_SIZE = int(os.getenv("DB_POOL_MIN_SIZE", "2"))
DB_POOL_MAX_SIZE = int(os.getenv("DB_POOL_MAX_SIZE", "10"))


@dataclass
class EtlStats:
    total_processed: int = 0
    features_computed: int = 0
    rollups_computed: int = 0
    anomalies_smoothed: int = 0
    last_run_at: Optional[datetime] = None
    errors: int = 0
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def increment(self, processed: int | bool = False, features: int | bool = False,
                        rollups: int | bool = False, smoothed: int | bool = False, error: int | bool = False):
        async with self._lock:
            if processed:
                self.total_processed += int(processed)
            if features:
                self.features_computed += int(features)
            if rollups:
                self.rollups_computed += int(rollups)
            if smoothed:
                self.anomalies_smoothed += int(smoothed)
            if error:
                self.errors += int(error)
            self.last_run_at = datetime.utcnow()

    def to_dict(self):
        return {
            "total_processed": self.total_processed,
            "features_computed": self.features_computed,
            "rollups_computed": self.rollups_computed,
            "anomalies_smoothed": self.anomalies_smoothed,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "errors": self.errors,
        }


class Database:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        if not self.pool:
            self.pool = await asyncpg.create_pool(
                dsn=DATABASE_URL,
                min_size=DB_POOL_MIN_SIZE,
                max_size=DB_POOL_MAX_SIZE,
            )

    async def disconnect(self):
        if self.pool:
            await self.pool.close()
            self.pool = None

    async def fetch(self, query: str, *args):
        if not self.pool:
            raise RuntimeError("Database pool not initialized. Call connect() first.")
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args):
        if not self.pool:
            raise RuntimeError("Database pool not initialized. Call connect() first.")
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def execute(self, query: str, *args):
        if not self.pool:
            raise RuntimeError("Database pool not initialized. Call connect() first.")
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def executemany(self, query: str, args):
        if not self.pool:
            raise RuntimeError("Database pool not initialized. Call connect() first.")
        async with self.pool.acquire() as conn:
            return await conn.executemany(query, args)


stats = EtlStats()
db = Database()
