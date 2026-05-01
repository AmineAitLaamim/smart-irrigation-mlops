import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
import uvicorn

from .database import db, stats
from .redis_consumer import consumer

DATA_INGESTION_PORT = int(os.getenv("DATA_INGESTION_PORT", "8001"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    await consumer.connect()
    consumer_task = asyncio.create_task(consumer.run())
    yield
    consumer._running = False
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass
    await consumer.disconnect()
    await db.disconnect()


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "stats": stats.to_dict(),
    }


def main():
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=DATA_INGESTION_PORT,
        log_level="info",
    )


if __name__ == "__main__":
    main()
