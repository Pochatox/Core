from logging import Logger

from pydantic import BaseModel


class BaseDBConfig(BaseModel):
    logger: Logger
    db_url: str

    class Config:
        arbitrary_types_allowed = True
