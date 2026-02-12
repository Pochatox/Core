# flake8-in-file-ignores: noqa: WPS115

from enum import IntEnum


class TaskPriority(IntEnum):
    LOW = 10
    MEDIUM = 20
    HIGH = 30
    VERY_HIGH = 40
    CRITICAL = 50


class UserRole(IntEnum):
    OWNER = 100
    MAINTAINER = 50
    MEMBER = 10
