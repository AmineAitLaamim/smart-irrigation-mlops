import os
import asyncio
import asyncpg
from typing import Optional, List
from dataclasses import dataclass, field
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://irrigation_user:changeme@timescaledb:5432/irrigation_db")
DB_POOL_MIN_SIZE = int(os.getenv("DB_POOL_MIN_SIZE", "2"))
DB_POOL_MAX_SIZE = int(os.getenv("DB_POOL_MAX_SIZE", "10"))


@dataclass
class QualityStats:
    total_checked: int = 0
    anomalies_found: int = 0
    rules_evaluated: int = 0
    last_run_at: Optional[datetime] = None
    errors: int = 0
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def increment(self, checked: bool = False, anomalies: bool = False,
                        rules: bool = False, error: bool = False):
        async with self._lock:
            if checked:
                self.total_checked += 1
            if anomalies:
                self.anomalies_found += 1
            if rules:
                self.rules_evaluated += 1
            if error:
                self.errors += 1
            self.last_run_at = datetime.utcnow()

    def to_dict(self):
        return {
            "total_checked": self.total_checked,
            "anomalies_found": self.anomalies_found,
            "rules_evaluated": self.rules_evaluated,
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

    async def fetch(self, query: str, *args) -> List[asyncpg.Record]:
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args) -> Optional[asyncpg.Record]:
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def execute(self, query: str, *args):
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def executemany(self, query: str, args):
        async with self.pool.acquire() as conn:
            return await conn.executemany(query, args)


stats = QualityStats()
db = Database()
