from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.config import AuthConfig, BoardConfig, TaskConfig
from app.db.enums import TaskPriority
from app.types import UserId, Username


class BaseDTO(BaseModel):
    ...


class RegistrationDTO(BaseDTO):
    username: str = Field(..., min_length=AuthConfig.username_min_length,
                          max_length=AuthConfig.username_max_length)
    email: str = Field(..., max_length=AuthConfig.email_max_length)
    password: str = Field(..., min_length=AuthConfig.password_min_length,
                          max_length=AuthConfig.password_max_length)
    first_name: str
    last_name: str
    avatar: str


class AuthDTO(BaseDTO):
    username: str = Field(..., min_length=AuthConfig.username_min_length,
                          max_length=AuthConfig.username_max_length)
    password: str = Field(..., min_length=AuthConfig.password_min_length,
                          max_length=AuthConfig.password_max_length)


class ChangeUserPasswordDTO(BaseDTO):
    password: str = Field(..., min_length=AuthConfig.password_min_length,
                          max_length=AuthConfig.password_max_length)


class UserDTO(BaseDTO):
    id: UserId
    username: Username
    email: str
    is_active: bool
    first_name: str
    last_name: str
    avatar: str
    created_at: datetime


class UserShortDTO(BaseDTO):
    username: Username
    first_name: str
    last_name: str
    avatar: str


class UserPreviewDTO(BaseDTO):
    username: Username
    avatar: str


class CreateBoardDTO(BaseDTO):
    name: str = Field(..., min_length=BoardConfig.min_name_length,
                      max_length=BoardConfig.max_name_length)
    description: Optional[str]


class LabelShortDTO(BaseDTO):
    name: str
    color: str


class LabelDTO(BaseDTO):
    id: UUID
    name: str
    color: str


class ShortTaskDTO(BaseDTO):
    assignee: UserPreviewDTO | None
    confirmed_by: UserPreviewDTO | None
    name: str
    description: str
    priority: TaskPriority
    created_at: datetime
    labels: list[LabelShortDTO]


class TaskPreviewDTO(BaseDTO):
    assignee: UserPreviewDTO | None
    confirmed_by: UserPreviewDTO | None
    name: str
    priority: TaskPriority
    created_at: datetime


class ColumnShortDTO(BaseDTO):
    name: str
    position: int
    wip: int
    tasks: list[ShortTaskDTO]


class ColumnPreviewDTO(BaseDTO):
    name: str
    position: int


class TaskTransitionDTO(BaseDTO):
    task: TaskPreviewDTO
    user: UserPreviewDTO
    column: ColumnPreviewDTO
    moved_at: datetime


class BoardDTO(BaseDTO):
    id: UUID
    owner: UserShortDTO
    name: str
    description: Optional[str]
    created_ad: datetime
    columns: list[ColumnShortDTO]
    labels: list[LabelDTO]


class CommentDTO(BaseDTO):
    author: UserPreviewDTO
    text: str
    created_at: datetime


class CreateTaskDTO(BaseDTO):
    board_id: UUID
    name: str = Field(..., min_length=TaskConfig.min_name_length,
                max_length=TaskConfig.max_name_length)
    description: str
    priority: TaskPriority
    labels: list[UUID]


class TaskDTO(BaseDTO):
    id: UUID
    board_id: UUID
    column: ColumnPreviewDTO | None
    assignee: UserShortDTO | None
    confirmed_by: UserShortDTO | None
    name: str
    description: str
    priority: TaskPriority
    created_at: datetime
    comments: list[CommentDTO]


class CreateColumnDTO(BaseDTO):
    board_id: UUID
    name: str = Field(..., min_length=BoardConfig.min_column_name,
                      max_length=BoardConfig.max_column_name)
    description: str | None
    wip: int
    position: int


class ColumnDTO(BaseDTO):
    id: UUID
    board_id: UUID
    name: str
    description: str | None
    position: int
    wip: int
    created_at: datetime
    tasks: list['ShortTaskDTO']


class CreateCommentDTO(BaseDTO):
    task_id: UUID
    text: str = Field(..., min_length=1,
                      max_length=TaskConfig.max_comment_length)


class CreateLabelDTO(BaseDTO):
    board_id: UUID
    name: str = Field(..., min_length=1,
                      max_length=BoardConfig.max_label_name)
    color: str


class MoveTaskDTO(BaseDTO):
    task_id: UUID
    move_to: int


class ConfirmTaskDTO(BaseDTO):
    task_id: UUID
