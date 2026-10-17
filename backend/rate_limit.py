import asyncio
import hashlib
import logging
import os
import time

from fastapi import HTTPException, Request
from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

_INCREMENT_WITH_EXPIRY = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return {count, redis.call('TTL', KEYS[1])}
"""


class AuthRateLimiter:
    def __init__(self) -> None:
        self.redis: Redis | None = None
        self.local: dict[str, tuple[int, float]] = {}
        self.local_lock = asyncio.Lock()

    async def initialize(self) -> None:
        redis_url = os.getenv("VERICERT_REDIS_URL")
        is_production = os.getenv("VERICERT_ENV", "development").strip().lower() == "production"
        if not redis_url:
            if is_production:
                raise RuntimeError("VERICERT_REDIS_URL is required in production")
            logger.warning("Using process-local authentication rate limits; configure Redis outside development")
            return
        self.redis = Redis.from_url(redis_url, decode_responses=False, socket_connect_timeout=3)
        try:
            await self.redis.ping()
        except RedisError as exc:
            await self.redis.aclose()
            self.redis = None
            raise RuntimeError("Configured authentication rate-limit Redis is unavailable") from exc

    async def close(self) -> None:
        if self.redis:
            await self.redis.aclose()
            self.redis = None

    async def check(self, request: Request, route: str, account: str, limit: int = 5, window: int = 300) -> None:
        client_ip = request.client.host if request.client else "unknown"
        identity = f"{route}:{client_ip}:{account.strip().lower()}"
        key = "vericert:auth-limit:" + hashlib.sha256(identity.encode("utf-8")).hexdigest()
        try:
            if self.redis:
                count, ttl = await self.redis.eval(_INCREMENT_WITH_EXPIRY, 1, key, window)
                count, ttl = int(count), max(int(ttl), 1)
            else:
                count, ttl = await self._check_local(key, limit, window)
        except RedisError as exc:
            logger.error("Authentication rate-limit service failed")
            raise HTTPException(status_code=503, detail="Authentication service temporarily unavailable") from exc

        if count > limit:
            raise HTTPException(
                status_code=429,
                detail="Too many authentication attempts. Try again later.",
                headers={"Retry-After": str(ttl)},
            )

    async def _check_local(self, key: str, limit: int, window: int) -> tuple[int, int]:
        now = time.monotonic()
        async with self.local_lock:
            current, expires_at = self.local.get(key, (0, now + window))
            if expires_at <= now:
                current, expires_at = 0, now + window
            current += 1
            self.local[key] = (current, expires_at)
            if len(self.local) > 10_000:
                self.local = {
                    saved_key: value
                    for saved_key, value in self.local.items()
                    if value[1] > now
                }
            return current, max(int(expires_at - now), 1)


rate_limiter = AuthRateLimiter()
