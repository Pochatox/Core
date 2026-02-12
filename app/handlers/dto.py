from pydantic import BaseModel, Field

from app.config import AuthConfig
from app.types import UserId, Username


class BaseDTO(BaseModel):
    ...


class RegistrationDTO(BaseDTO):
    username: str = Field(..., min_length=AuthConfig.username_min_length,
                          max_length=AuthConfig.username_max_length)
    email: str = Field(..., max_length=AuthConfig.email_max_length)
    password: str = Field(..., min_length=AuthConfig.password_min_length,
                          max_length=AuthConfig.password_max_length)


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
