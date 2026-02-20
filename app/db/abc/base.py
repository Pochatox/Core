from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, Literal, Optional, TypeVar
from uuid import UUID

import uuid6

from app.db.abc.configs import BaseDBConfig
from app.db.abc.models import BoardProtocol, UserProtocol
from app.types import Sentinel, UserId, Username

DBConfig = TypeVar('DBConfig', bound=BaseDBConfig)


def get_id() -> uuid6.UUID:
    return uuid6.uuid7()


def str_to_id(str_id: str) -> UUID:
    try:
        return UUID(str_id)
    except ValueError as e:
        raise ValueError(f'Invalid id {str_id}') from e


@dataclass
class BaseAsyncDB(ABC, Generic[DBConfig]):
    config: DBConfig

    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...

    ###
    # User model
    ###

    @abstractmethod
    async def get_user(self, id: UserId) -> UserProtocol: ...

    @abstractmethod
    async def get_user_by_username(self, username: Username) -> UserProtocol: ...

    @abstractmethod
    async def get_user_email(self, id: UserId) -> str: ...

    @abstractmethod
    async def create_user(
        self, username: str, password: str, email: str, is_active: bool,
        first_name: str, last_name: str, avatar: str, id: UserId = Sentinel
    ) -> UserProtocol: ...

    @abstractmethod
    async def del_user(self, id: UserId) -> None: ...

    @abstractmethod
    async def change_user_password(self, id: UserId, new_password: str) -> None: ...

    @abstractmethod
    async def is_user_username_email_unique(
        self, username: str, email: str
    ) -> Literal[True]: ...

    @abstractmethod
    async def verify_username_password(
        self, username: Username, password: str
    ) -> UserId: ...

    @abstractmethod
    async def is_user_active(self, id: UserId) -> bool: ...

    @abstractmethod
    async def activate_user(self, username: Username) -> UserId: ...

    @abstractmethod
    async def create_board(
        self, owner_id: UserId, name: str, description: Optional[str] = None
    ) -> BoardProtocol: ...
