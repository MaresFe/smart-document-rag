from collections import deque
from dataclasses import dataclass
from hashlib import sha256
from math import ceil
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request, status

from app.core.config import settings


RATE_LIMIT_DETAIL = (
    "Too many requests. Please try again later."
)


@dataclass(frozen=True)
class RateLimitPolicy:
    max_attempts: int
    window_seconds: int


class SlidingWindowRateLimiter:
    def __init__(self) -> None:
        self._attempts: dict[str, deque[float]] = {}
        self._last_seen: dict[str, float] = {}
        self._lock = Lock()

    def hit(
        self,
        *,
        key: str,
        policy: RateLimitPolicy,
        max_keys: int,
    ) -> int | None:
        now = monotonic()
        cutoff = now - policy.window_seconds

        with self._lock:
            attempts = self._attempts.get(key)

            if attempts is None:
                self._make_room(
                    now=now,
                    max_keys=max_keys,
                )
                attempts = deque()
                self._attempts[key] = attempts

            while attempts and attempts[0] <= cutoff:
                attempts.popleft()

            self._last_seen[key] = now

            if len(attempts) >= policy.max_attempts:
                retry_after = ceil(
                    policy.window_seconds
                    - (now - attempts[0])
                )
                return max(1, retry_after)

            attempts.append(now)
            return None

    def clear(self, key: str | None = None) -> None:
        with self._lock:
            if key is None:
                self._attempts.clear()
                self._last_seen.clear()
                return

            self._attempts.pop(key, None)
            self._last_seen.pop(key, None)

    def _make_room(
        self,
        *,
        now: float,
        max_keys: int,
    ) -> None:
        if len(self._attempts) < max_keys:
            return

        oldest_keys = sorted(
            self._last_seen,
            key=self._last_seen.get,
        )
        remove_count = max(1, max_keys // 10)

        for key in oldest_keys[:remove_count]:
            self._attempts.pop(key, None)
            self._last_seen.pop(key, None)


auth_rate_limiter = SlidingWindowRateLimiter()


def get_client_identifier(request: Request) -> str:
    if request.client is None:
        return "unknown-client"

    return request.client.host


def build_rate_limit_key(
    *,
    scope: str,
    request: Request,
    identity: str,
) -> str:
    normalized_identity = identity.strip().casefold()
    raw_key = "|".join(
        [
            scope,
            get_client_identifier(request),
            normalized_identity,
        ]
    )

    return sha256(raw_key.encode("utf-8")).hexdigest()


def enforce_auth_rate_limit(
    *,
    scope: str,
    request: Request,
    identity: str,
    policy: RateLimitPolicy,
) -> str:
    key = build_rate_limit_key(
        scope=scope,
        request=request,
        identity=identity,
    )
    client_key = build_rate_limit_key(
        scope=f"{scope}-client",
        request=request,
        identity="all-identities",
    )

    if not settings.auth_rate_limit_enabled:
        return key

    identity_retry_after = auth_rate_limiter.hit(
        key=key,
        policy=policy,
        max_keys=settings.auth_rate_limit_max_keys,
    )
    client_retry_after = auth_rate_limiter.hit(
        key=client_key,
        policy=RateLimitPolicy(
            max_attempts=policy.max_attempts * 5,
            window_seconds=policy.window_seconds,
        ),
        max_keys=settings.auth_rate_limit_max_keys,
    )

    retry_values = [
        retry_after
        for retry_after in (
            identity_retry_after,
            client_retry_after,
        )
        if retry_after is not None
    ]

    if retry_values:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=RATE_LIMIT_DETAIL,
            headers={
                "Retry-After": str(max(retry_values)),
            },
        )

    return key


def clear_auth_rate_limit(key: str) -> None:
    auth_rate_limiter.clear(key)


def reset_auth_rate_limits() -> None:
    auth_rate_limiter.clear()
