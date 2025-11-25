from typing import Any, Optional

import redis

from app.core.config import settings


class RedisClient:
    def __init__(
        self,
        host: str = settings.REDIS_HOST,
        port: int = settings.REDIS_PORT,
        db: int = settings.REDIS_DB,
        password: Optional[str] = settings.REDIS_PASSWORD,
    ):
        self.client = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True,
        )

    def get(
        self,
        key: str,
    ) -> Optional[str]:
        return self.client.get(key)

    def set(
        self,
        key: str,
        value: Any,
        ex: Optional[int] = None,
    ) -> bool:
        return self.client.set(key, str(value), ex=ex)

    def delete(
        self,
        key: str,
    ) -> int:
        return self.client.delete(key)

    def exists(
        self,
        key: str,
    ) -> bool:
        return bool(self.client.exists(key))

    def incr(
        self,
        key: str,
        amount: int = 1,
    ) -> int:
        return self.client.incrby(key, amount)

    def decr(
        self,
        key: str,
        amount: int = 1,
    ) -> int:
        return self.client.decrby(key, amount)

    def hget(
        self,
        name: str,
        key: str,
    ) -> Optional[str]:
        return self.client.hget(name, key)

    def hset(
        self,
        name: str,
        key: str,
        value: Any,
    ) -> int:
        return self.client.hset(name, key, str(value))

    def hgetall(
        self,
        name: str,
    ) -> dict[str, str]:
        return self.client.hgetall(name)


redis_client = RedisClient()

