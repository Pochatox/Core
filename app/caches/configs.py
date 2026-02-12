import logging
from datetime import timedelta

from pydantic import BaseModel

from app.types import Seconds


class BaseTTLCacheConfig(BaseModel):
    logger: logging.Logger
    default_cache_lifetime: Seconds | timedelta = 60

    class Config:
        arbitrary_types_allowed = True


class RedisConfig(BaseTTLCacheConfig):
    redis_host: str
    redis_port: int
