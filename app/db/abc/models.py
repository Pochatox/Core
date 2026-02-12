from typing import Protocol
from datetime import datetime
from uuid import UUID


class UserProtocol(Protocol):
    id: UUID
    username: str
    password: str
    email: str
    is_active: bool
    role: int
    first_name: str
    last_name: str
    avatar: str
    created_at: datetime


class BoardProtocol(Protocol):
    id: UUID
    owner_id: UUID
    name: str
    created_at: datetime


class ColumnProtocol(Protocol):
    id: UUID
    board_id: UUID
    name: str
    description: str | None
    position: int
    wip: int
    created_at: datetime


class TaskProtocol(Protocol):
    id: UUID
    board_id: UUID
    column_id: UUID
    assignee_id: UUID | None
    name: str
    description: str
    priority: int
    created_at: datetime


class LabelProtocol(Protocol):
    id: UUID
    board_id: UUID
    name: str
    color: str


class CommentProtocol(Protocol):
    id: UUID
    task_id: UUID
    author_id: UUID
    text: str
    created_at: datetime


class TaskTransitionProtocol(Protocol):
    id: UUID
    task_id: UUID
    user_id: UUID
    column_id: UUID
    moved_at: datetime


class TaskLabelProtocol(Protocol):
    task: UUID
    label: UUID
