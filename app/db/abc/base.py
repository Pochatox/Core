from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, Literal, Optional, TypeVar
from uuid import UUID

import uuid6

from app.db.abc.configs import BaseDBConfig
from app.db.abc.models import (BoardProtocol, ColumnProtocol, CommentProtocol,
                               LabelProtocol, RoleProtocol, TaskProtocol,
                               TaskTransitionProtocol, UserProtocol)
from app.db.enums import TaskPriority, UserRole
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
    async def create_user(
        self, username: str, password: str, email: str, is_active: bool,
        first_name: str, last_name: str, avatar: str, id: UserId = Sentinel
    ) -> UserProtocol: ...

    @abstractmethod
    async def get_short_user(self, user_id: UserId) -> UserProtocol: ...

    @abstractmethod
    async def get_user_email_by_username(self, username: str) -> str: ...

    @abstractmethod
    async def get_user_email(self, user_id: UserId) -> str: ...

    @abstractmethod
    async def del_user(self, id: UserId) -> None: ...

    @abstractmethod
    async def change_user_password(self, id: UserId, new_password: str) -> None: ...

    @abstractmethod
    async def is_user_username_email_unique(
        self, username: str, email: str
    ) -> Literal[True]: ...

    @abstractmethod
    async def is_user_active(self, id: UserId) -> bool: ...

    @abstractmethod
    async def activate_user(self, username: Username) -> UserId: ...

    @abstractmethod
    async def verify_username_password(
        self, username: Username, password: str
    ) -> UserId: ...

    @abstractmethod
    async def create_board(
        self, owner_id: UserId, name: str, description: Optional[str] = None
    ) -> BoardProtocol: ...

    @abstractmethod
    async def get_board(self, board_id: UUID) -> BoardProtocol: ...

    @abstractmethod
    async def is_user_in_board(self, user_id: UserId, board_id: UUID) -> bool: ...

    @abstractmethod
    async def is_user_in_board_by_column(
        self, user_id: UserId, column_id: UUID
    ) -> bool: ...

    @abstractmethod
    async def is_user_in_board_by_task(
        self, user_id: UserId, task_id: UUID
    ) -> bool: ...

    @abstractmethod
    async def create_column(
        self, board_id: UUID, name: str, description: Optional[str], position: int,
        wip: int
    ) -> ColumnProtocol: ...

    @abstractmethod
    async def create_comment(
        self, task_id: UUID, author_id: UUID, text: str
    ) -> CommentProtocol: ...

    @abstractmethod
    async def create_task(
        self, board_id: UUID, assign_id: UUID | None,
        confirmed_by_id: UUID | None, name: str, description: str,
        priority: TaskPriority, user_id: UserId, label_ids: list[UUID]
    ) -> TaskProtocol: ...

    @abstractmethod
    async def get_user_role(self, user_id: UserId, board_id: UUID) -> UserRole: ...

    @abstractmethod
    async def get_column(self, column_id: UUID) -> ColumnProtocol: ...

    @abstractmethod
    async def get_task(self, task_id: UUID) -> TaskProtocol: ...

    @abstractmethod
    async def get_user_username_avatar(self, user_id: UUID) -> UserProtocol: ...

    @abstractmethod
    async def create_label(
        self, board_id: UUID, name: str, color: str
    ) -> LabelProtocol: ...

    @abstractmethod
    async def task_transit(
        self, task_id: UUID, user_id: UserId, move_to: int
    ) -> None: ...

    @abstractmethod
    async def is_users_task(self, user_id: UserId, task_id: UUID) -> bool: ...

    @abstractmethod
    async def confirm_task(self, user_id: UserId, task_id: UUID) -> None: ...

    @abstractmethod
    async def assigne_task(self, user_id: UserId, task_id: UUID) -> None: ...

    @abstractmethod
    async def get_board_id_by_task(self, task_id: UUID) -> UUID: ...

    @abstractmethod
    async def get_confirmed_tasks(self, board_id: UUID) -> list[TaskProtocol]: ...

    @abstractmethod
    async def get_not_assigned_tasks(self, board_id: UUID) -> list[TaskProtocol]: ...

    @abstractmethod
    async def get_task_transitions(
        self, board_id: UUID
    ) -> list[TaskTransitionProtocol]: ...

    @abstractmethod
    async def get_user_names(self, user_id: UserId) -> UserProtocol: ...

    @abstractmethod
    async def get_board_name_created_at(self, board_id: UUID) -> BoardProtocol: ...

    @abstractmethod
    async def create_role(
        self, user_id: UserId, board_id: UUID, role: UserRole
    ) -> RoleProtocol: ...

    @abstractmethod
    async def is_move_to_column_allowed_by_task(
        self, task_id: UUID, column_position: int,
    ) -> bool: ...

    @abstractmethod
    async def delete_role(
        self, user_id: UserId, board_id: UUID
    ) -> None: ...

    @abstractmethod
    async def get_users_boards(
        self, user_id: UserId
    ) -> list[tuple[BoardProtocol, UserRole]]: ...

    @abstractmethod
    async def is_task_in_last_column(self, task_id: UUID, board_id: UUID) -> bool: ...

    @abstractmethod
    async def create_maintainer(self, board_id: UUID, user_id: UserId) -> None: ...

    @abstractmethod
    async def get_user_id_by_username(self, username: str) -> UserId: ...

    @abstractmethod
    async def get_users_list(
        self, board_id: UUID
    ) -> list[tuple[UserProtocol, UserRole]]: ...
