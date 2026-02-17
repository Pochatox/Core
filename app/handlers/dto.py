from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.config import AuthConfig
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
    name: str
    description: Optional[str]


class BoardDTO(BaseDTO):
    id: UUID
    owner: UserShortDTO
    name: str
    description: Optional[str]
    created_ad: datetime
    columns: list['ColumnShortDTO']


class ColumnShortDTO(BaseDTO):
    name: str
    position: int
    wip: int
    tasks: list['ShortTaskDTO']


class ShortTaskDTO(BaseDTO):
    assigne: UserPreviewDTO
    confirmed_by: UserPreviewDTO
    name: str
    description: str
    priority: TaskPriority
    created_at: datetime
    labels: list['LabelShortDTO']


class LabelShortDTO(BaseDTO):
    name: str
    color: str
