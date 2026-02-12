# flake8-in-file-ignores: noqa: WPS204, WPS203

from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncGenerator, NoReturn

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)

from app.db.abc.base import BaseAsyncDB
from app.db.exc import DatabaseError
from app.db.sqlalchemy.config import SQLAlchemyDBConfig
from app.db.sqlalchemy.models import Base


class DatabaseWriteError(Exception): ...


@dataclass
class AsyncSQLAlchemyDB(BaseAsyncDB[SQLAlchemyDBConfig]):

    async def connect(self) -> None:
        self.engine = create_async_engine(
            url=self.config.db_url,
            **self.config.engine_kwargs
        )
        self.sessionmaker = async_sessionmaker(
            bind=self.engine,
            **self.config.session_maker_kwargs
        )

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    @asynccontextmanager
    async def get_read_session(self) -> AsyncGenerator[AsyncSession, None]:
        def prevent_modifications(*args, **kwargs) -> NoReturn:  # noqa: ANN002
            raise DatabaseWriteError(
                'Modifications are not allowed in read-only session'
            )
        async with self.sessionmaker() as session:
            session: AsyncSession
            session.flush = prevent_modifications
            yield session

    @asynccontextmanager
    async def get_write_session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self.sessionmaker() as session:
            session: AsyncSession
            try:
                yield session
                await session.commit()
            except SQLAlchemyError as e:
                await session.rollback()
                raise DatabaseError from e

    async def close(self) -> None:
        await self.engine.dispose()
