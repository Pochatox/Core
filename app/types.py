from typing import Any, TypeAlias
from uuid import UUID

Sentinel: Any = object
Seconds: TypeAlias = int

RegistrationToken: TypeAlias = str
AccessToken: TypeAlias = str
RefreshToken: TypeAlias = str
ChangePasswordToken: TypeAlias = str

UserId: TypeAlias = UUID
Username: TypeAlias = UUID
