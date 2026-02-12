from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar

from ulid import ULID

from app.db.abc.configs import BaseDBConfig

DBConfig = TypeVar('DBConfig', bound=BaseDBConfig)


def get_id() -> str:
    return str(ULID())


@dataclass
class BaseAsyncDB(ABC, Generic[DBConfig]):
    config: DBConfig

    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...
