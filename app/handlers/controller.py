from typing import Generic, TypeVar

from litestar.controller import Controller

from app.config import BaseConfig

ConfigType = TypeVar('ConfigType', bound=BaseConfig)


class BaseController(Controller, Generic[ConfigType]):
    config: ConfigType
    path: str
