from typing import Any, Mapping

from pydantic import Field

from app.db.abc.configs import BaseDBConfig


class SQLAlchemyDBConfig(BaseDBConfig):
    engine_kwargs: Mapping[str, Any] = Field(default_factory=dict)
    session_maker_kwargs: Mapping[str, Any] = Field(default_factory=dict)
