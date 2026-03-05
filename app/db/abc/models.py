from __future__ import annotations

from datetime import datetime
from typing import List, Protocol
from uuid import UUID

from app.db.enums import Avatar, TaskPriority, UserRole
from app.types import UserId, Username


class UserProtocol(Protocol):
    id: UserId
    username: Username
    password: str
    email: str
    is_active: bool
    first_name: str
    last_name: str
    avatar: Avatar
    created_at: datetime

    boards: List[BoardProtocol]
    tasks: List[TaskProtocol]
    confirmed_tasks: List[TaskProtocol]
    comments: List[CommentProtocol]
    transitions: List[TaskTransitionProtocol]
    roles: List[RoleProtocol]


class BoardProtocol(Protocol):
    id: UUID
    owner_id: UUID
    name: str
    description: str
    created_at: datetime

    owner: UserProtocol
    columns: List[ColumnProtocol]
    tasks: List[TaskProtocol]
    labels: List[LabelProtocol]
    roles: List[RoleProtocol]


class ColumnProtocol(Protocol):
    id: UUID
    board_id: UUID
    name: str
    description: str | None
    position: int
    wip: int
    created_at: datetime

    board: BoardProtocol
    tasks: List[TaskProtocol]
    transitions: List[TaskTransitionProtocol]


class TaskProtocol(Protocol):
    id: UUID
    board_id: UUID
    column_id: UUID
    created_by_id: UserId
    assignee_id: UUID | None
    confirmed_by_id: UUID | None
    name: str
    description: str
    priority: TaskPriority
    created_at: datetime

    board: BoardProtocol
    column: ColumnProtocol
    assignee: UserProtocol | None
    confirmed_by: UserProtocol | None
    comments: List[CommentProtocol]
    transitions: List[TaskTransitionProtocol]
    labels: List[LabelProtocol]


class LabelProtocol(Protocol):
    id: UUID
    board_id: UUID
    name: str
    color: str

    board: BoardProtocol
    tasks: List[TaskProtocol]


class CommentProtocol(Protocol):
    id: UUID
    task_id: UUID
    author_id: UUID
    text: str
    created_at: datetime

    task: TaskProtocol
    author: UserProtocol


class TaskTransitionProtocol(Protocol):
    id: UUID
    task_id: UUID
    user_id: UserId
    column_id: UUID
    moved_at: datetime

    task: TaskProtocol
    user: UserProtocol
    column: ColumnProtocol


class RoleProtocol(Protocol):
    id: UUID
    user_id: UserId
    board_id: UUID
    role: UserRole

    user: UserProtocol
    board: BoardProtocol
