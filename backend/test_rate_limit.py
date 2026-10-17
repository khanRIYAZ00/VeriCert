import asyncio
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from .rate_limit import AuthRateLimiter


class SharedCounter:
    def __init__(self):
        self.counts = {}

    async def eval(self, script, key_count, key, window):
        count = self.counts.get(key, 0) + 1
        self.counts[key] = count
        return count, window


def test_request():
    return SimpleNamespace(client=SimpleNamespace(host="192.0.2.5"))


class RateLimitTests(unittest.TestCase):
    def test_rate_limit_is_shared_between_limiter_instances(self):
        shared_counter = SharedCounter()
        instances = [AuthRateLimiter(), AuthRateLimiter()]
        for instance in instances:
            instance.redis = shared_counter

        async def consume():
            for index in range(5):
                await instances[index % 2].check(
                    test_request(),
                    "login",
                    "student@example.test",
                    limit=5,
                )
            with self.assertRaises(HTTPException) as raised:
                await instances[0].check(
                    test_request(),
                    "login",
                    "student@example.test",
                    limit=5,
                )
            self.assertEqual(raised.exception.status_code, 429)
            self.assertIn("Retry-After", raised.exception.headers)

        asyncio.run(consume())

    def test_production_requires_redis_instead_of_local_fallback(self):
        limiter = AuthRateLimiter()
        with patch.dict(os.environ, {"VERICERT_ENV": "production"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "VERICERT_REDIS_URL is required"):
                asyncio.run(limiter.initialize())
        self.assertIsNone(limiter.redis)


if __name__ == "__main__":
    unittest.main()
