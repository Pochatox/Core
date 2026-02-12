from datetime import timedelta
from logging import Logger

from kapusta import BaseCRUD
from pydantic import BaseModel

from app.types import Seconds


class BaseTaskManagerConfig(BaseModel):
    logger: Logger

    class Config:
        arbitrary_types_allowed = True


class KapustaConfig(BaseTaskManagerConfig):
    crud: BaseCRUD
    max_tick_interval: Seconds
    default_overdue_time_delta: timedelta | None
    default_max_retry_attempts: int
    default_timeout: Seconds
