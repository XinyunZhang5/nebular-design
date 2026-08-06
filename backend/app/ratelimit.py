"""A token bucket, in memory, keyed by whatever the caller wants to limit on.

In memory because there is one process. That is a real limit and worth stating
rather than discovering: the counters live in this process's heap, so they reset
on every deploy and they are not shared if a second instance is ever started.
The moment this app runs on more than one machine, an attacker gets N times the
allowance and the fix is to move the buckets to Redis. Until then a dictionary is
the right amount of machinery, and it is the difference between a login endpoint
that can be brute-forced at network speed and one that cannot.

Not a decorator: the interesting limits here key on the request body (the email
being guessed) as well as the client address, and a decorator cannot see that.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class Bucket:
    """Refills at `rate` per second, holds at most `burst`."""

    rate: float
    burst: float
    tokens: float = field(default=0.0)
    updated: float = field(default_factory=time.monotonic)

    def take(self, cost: float = 1.0) -> bool:
        now = time.monotonic()
        self.tokens = min(self.burst, self.tokens + (now - self.updated) * self.rate)
        self.updated = now
        if self.tokens >= cost:
            self.tokens -= cost
            return True
        return False


class RateLimiter:
    def __init__(self, rate: float, burst: float, ttl: float = 3600.0) -> None:
        self.rate, self.burst, self.ttl = rate, burst, ttl
        self._buckets: dict[str, Bucket] = {}
        self._swept = time.monotonic()

    def allow(self, key: str, cost: float = 1.0) -> bool:
        self._sweep()
        bucket = self._buckets.get(key)
        if bucket is None:
            bucket = Bucket(self.rate, self.burst, tokens=self.burst)
            self._buckets[key] = bucket
        return bucket.take(cost)

    def _sweep(self) -> None:
        """Drop buckets nobody has touched, so the dict is not a memory leak."""
        now = time.monotonic()
        if now - self._swept < 60:
            return
        self._swept = now
        cutoff = now - self.ttl
        for key in [k for k, b in self._buckets.items() if b.updated < cutoff]:
            del self._buckets[key]


# Five attempts, then one more every twelve seconds. Slow enough that guessing a
# six-character password over the network is not worth starting, fast enough that
# a person who mistypes theirs three times notices nothing.
login_limiter = RateLimiter(rate=1 / 12, burst=5)

# Registration is rarer and more expensive (bcrypt, a database write), so it is
# tighter: three in a burst, one more every two minutes.
register_limiter = RateLimiter(rate=1 / 120, burst=3)

# Chat, per connection. Generous for a person typing, useless for a script.
chat_limiter = RateLimiter(rate=1.0, burst=8)


def client_key(request) -> str:
    """Best available client identity. Behind a proxy that is a forwarded header.

    Fly, Render and Vercel all terminate TLS in front of the app, so the socket
    address is the proxy's and is identical for every caller — limiting on it
    would rate-limit the whole internet as one client. The leftmost entry of
    X-Forwarded-For is the original client, and it is only trustworthy because
    the proxy in front of us rewrites it; exposed directly, it is spoofable.
    """
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
