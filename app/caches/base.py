from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import timedelta
from typing import Generic, Optional, Self, TypeVar

from redis import asyncio as aioredis

from app.caches.configs import BaseTTLCacheConfig, RedisConfig
from app.types import Seconds

CacheConfig = TypeVar('CacheConfig', bound=BaseTTLCacheConfig)


@dataclass
class BaseAsyncTTLCache(ABC, Generic[CacheConfig]):
    config: CacheConfig

    @abstractmethod
    async def connect(self) -> Self: ...

    @abstractmethod
    async def set(
        self, key: str, value: str,  # noqa: WPS110
        time: Optional[Seconds | timedelta] = None
    ) -> None: ...

    @abstractmethod
    async def get(self, key: str) -> str | None: ...

    @abstractmethod
    async def del_key(self, key: str) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...


@dataclass
class RedisAsyncCache(BaseAsyncTTLCache[RedisConfig]):

    async def connect(self) -> Self:
        self.redis = aioredis.Redis(
            host=self.config.redis_host,
            port=self.config.redis_port
        )
        self.config.logger.info('Redis: connect')
        return self

    async def set(
        self, key: str, value: str,  # noqa: WPS110
        time: Optional[Seconds | timedelta] = None
    ) -> None:
        try:
            await self.redis.set(
                name=key,
                value=value,
                ex=time if time else self.config.default_cache_lifetime
            )
            self.config.logger.debug(f'Set cache value with key: {key}')
        except Exception as e:
            self.config.logger.warning(e, exc_info=True)

    async def get(self, key: str) -> str | None:
        try:
            cached_value = await self.redis.get(name=key)
            self.config.logger.debug(f'Get value by key: {key}')
            return cached_value.decode() if cached_value else None
        except Exception as e:
            self.config.logger.warning(e, exc_info=True)

    async def del_key(self, key: str) -> None:
        try:
            await self.redis.delete(key)
            self.config.logger.debug(f'Deleted cache key: {key}')
        except Exception as e:
            self.config.logger.warning(e, exc_info=True)

    async def close(self) -> None:
        await self.redis.aclose()
        self.config.logger.info('Redis: close')
