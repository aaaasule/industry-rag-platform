"""应用层 Redis 限流：用户 QPS 滑动窗口 + 租户 chat 并发信号量。"""

from __future__ import annotations

import time
import uuid
from typing import Literal

import redis

from app.platform.config import Settings, get_settings
from app.platform.errors import RateLimited
from app.platform.logging import get_logger

logger = get_logger(__name__)

QPS_WINDOW_SECONDS = 60
LEASE_TTL_SECONDS = 600
INFLIGHT_KEY_TTL_SECONDS = 3600

RouteName = Literal["chat", "search"]


class RateLimiter:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def check_user_qps(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        route: RouteName,
    ) -> None:
        limit = int(self._settings.rate_limit_user_per_minute)
        if limit <= 0:
            return
        key = f"irp:rl:qps:{tenant_id}:{user_id}:{route}"
        now = time.time()
        member = f"{now:.6f}:{uuid.uuid4()}"
        try:
            client = self._client()
            pipe = client.pipeline()
            pipe.zremrangebyscore(key, 0, now - QPS_WINDOW_SECONDS)
            pipe.zcard(key)
            results = pipe.execute()
            count = int(results[1])
            if count >= limit:
                retry_after = self._qps_retry_after(client, key, now)
                raise RateLimited(
                    details={
                        "limit": limit,
                        "window_seconds": QPS_WINDOW_SECONDS,
                        "route": route,
                    },
                    retry_after_seconds=retry_after,
                )
            pipe2 = client.pipeline()
            pipe2.zadd(key, {member: now})
            pipe2.expire(key, QPS_WINDOW_SECONDS + 1)
            pipe2.execute()
        except RateLimited:
            raise
        except Exception as exc:
            logger.warning("rate_limit_qps_failed", error=str(exc), route=route)

    def acquire_chat_slot(self, *, tenant_id: uuid.UUID) -> str | None:
        """占用租户 chat 并发名额；返回 lease_id。limit≤0 时返回 None（无需释放）。"""
        limit = int(self._settings.rate_limit_tenant_chat_concurrency)
        if limit <= 0:
            return None
        inflight_key = f"irp:rl:inflight:{tenant_id}:chat"
        lease_id = str(uuid.uuid4())
        lease_key = f"irp:rl:lease:{tenant_id}:{lease_id}"
        try:
            client = self._client()
            current = int(client.incr(inflight_key))
            client.expire(inflight_key, INFLIGHT_KEY_TTL_SECONDS)
            if current > limit:
                client.decr(inflight_key)
                raise RateLimited(
                    message="租户并发问答已达上限，请稍后重试",
                    details={"limit": limit, "route": "chat", "kind": "concurrency"},
                    retry_after_seconds=5,
                )
            client.set(lease_key, "1", ex=LEASE_TTL_SECONDS)
            return lease_id
        except RateLimited:
            raise
        except Exception as exc:
            logger.warning("rate_limit_concurrency_acquire_failed", error=str(exc))
            return None

    def release_chat_slot(self, *, tenant_id: uuid.UUID, lease_id: str | None) -> None:
        if not lease_id:
            return
        inflight_key = f"irp:rl:inflight:{tenant_id}:chat"
        lease_key = f"irp:rl:lease:{tenant_id}:{lease_id}"
        try:
            client = self._client()
            removed = int(client.delete(lease_key))
            if removed:
                val = int(client.decr(inflight_key))
                if val < 0:
                    client.set(inflight_key, 0)
        except Exception as exc:
            logger.warning("rate_limit_concurrency_release_failed", error=str(exc))

    def _client(self) -> redis.Redis:
        return redis.from_url(self._settings.redis_url, decode_responses=True)

    @staticmethod
    def _qps_retry_after(client: redis.Redis, key: str, now: float) -> int:
        oldest = client.zrange(key, 0, 0, withscores=True)
        if not oldest:
            return QPS_WINDOW_SECONDS
        first = oldest[0]
        if not isinstance(first, (tuple, list)) or len(first) < 2:
            return QPS_WINDOW_SECONDS
        score = float(first[1])
        return max(1, int(QPS_WINDOW_SECONDS - (now - score)) + 1)
