from json import JSONEncoder
from logging import Logger
from typing import Optional

from pydantic import BaseModel


class BaseTokenConfig(BaseModel):
    logger: Logger

    class Config:
        arbitrary_types_allowed = True


class JWTokenConfig(BaseTokenConfig):
    alg: str
    typ: str
    key: str
    json_encoder: Optional[type[JSONEncoder]] = None
    sort_headers: bool = True
