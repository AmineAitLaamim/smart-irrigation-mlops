import os
import time
from fastapi import HTTPException, Request, status
import redis


RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "100"))
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")


class RateLimiter:
    def __init__(self, redis_url: str = REDIS_URL, limit: int = RATE_LIMIT_PER_MIN):
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        self.limit = limit
        self.window = 60

    async def check_rate_limit(self, client_ip: str) -> bool:
        key = f"rate_limit:{client_ip}"
        current_time = int(time.time())
        window_start = current_time - self.window

        pipe = self.redis_client.pipeline()
        pipe.zremrangebyscore(key, "-inf", str(window_start))
        pipe.zcard(key)
        pipe.zadd(key, {str(current_time): current_time})
        pipe.expire(key, self.window)
        results = pipe.execute()

        request_count = results[1]
        return request_count < self.limit

    async def get_remaining(self, client_ip: str) -> int:
        key = f"rate_limit:{client_ip}"
        current_time = int(time.time())
        window_start = current_time - self.window

        self.redis_client.zremrangebyscore(key, "-inf", str(window_start))
        count = self.redis_client.zcard(key)
        return max(0, self.limit - count)


rate_limiter = RateLimiter()


async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"

    if client_ip == "unknown":
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()

    allowed = await rate_limiter.check_rate_limit(client_ip)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": "60"},
        )

    remaining = await rate_limiter.get_remaining(client_ip)
    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(RATE_LIMIT_PER_MIN)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    return response