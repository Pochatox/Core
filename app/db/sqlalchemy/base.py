# flake8-in-file-ignores: noqa: WPS110, WPS204, WPS203, WPS615

from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncGenerator, Literal, NoReturn, Optional, Sequence
from uuid import UUID

from sqlalchemy import and_, case, delete, exists, func, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)
from sqlalchemy.orm import selectinload

from app.db.abc.base import BaseAsyncDB, get_id
from app.db.abc.models import (BoardProtocol, ColumnProtocol, TaskProtocol,
                               UserProtocol)
from app.db.enums import TaskPriority, UserRole
from app.db.exc import (ActivateUserError, BoardNotFoundError, ColumnNotExist,
                        DatabaseError, InvalidColumnPosition, InvalidCredentialsError,
                        UniqueEmailError, UniqueUsernameError,
                        UserNotFoundError)
from app.db.sqlalchemy.config import SQLAlchemyDBConfig
from app.db.sqlalchemy.models import (Base, Board, Column, Label, Role, Task,
                                      TaskTransition, User)
from app.types import Sentinel, UserId, Username


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

    async def close(self) -> None:
        await self.engine.dispose()

    async def create_user(
        self, username: str, password: str, email: str, is_active: bool,
        first_name: str, last_name: str, avatar: str, id: UserId = Sentinel
    ) -> UserProtocol:
        try:
            async with self._get_write_session() as session:
                new_user = User(
                    id=get_id() if id is Sentinel else id,
                    username=username,
                    email=email,
                    is_active=is_active,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    avatar=avatar
                )
                session.add(new_user)

        except DatabaseError as e:
            if isinstance(e.__cause__, IntegrityError):
                self._raise_user_unique_error(e.__cause__)
            else:
                raise e

        return new_user

    async def get_user(self, id: UserId) -> UserProtocol:
        async with self._get_read_session() as session:
            user = await session.get(User, id)
            if not user:
                raise UserNotFoundError(f'User with id {id} is not found')
            return user  # type: ignore

    async def get_user_by_username(self, username: Username) -> UserProtocol:
        async with self._get_read_session() as session:
            stmt = select(User).where(User.username == username)
            user = (await session.execute(stmt)).scalar_one_or_none()
            if not user:
                raise UserNotFoundError(f'User with username {username} is not found')
            return user  # type: ignore

    async def get_user_email(self, id: UserId) -> str:
        async with self._get_read_session() as session:
            stmt = select(User.email).where(User.id == id)
            email = (await session.execute(stmt)).scalar_one_or_none()
            if not email:
                raise UserNotFoundError(f'User with id {id} is not found')
            return email

    async def del_user(self, id: UserId) -> None:
        async with self._get_write_session() as session:
            await session.execute(delete(User).where(User.id == id))

    async def change_user_password(self, id: UserId, new_password: str) -> None:
        async with self._get_write_session() as session:
            user = await session.get(User, id)
            if user:
                user.password = new_password
                session.add(user)
            else:
                raise UserNotFoundError(f'User with id {id} is not found')

    async def is_user_username_email_unique(
        self, username: str, email: str
    ) -> Literal[True]:
        async with self._get_read_session() as session:
            stmt = (
                select(
                    case(
                        (User.email == email, 'email'),
                        (User.username == username, 'username')
                    )
                )
                .where((User.email == email) | (User.username == username))
            )
            non_unique_fields = (await session.execute(stmt)).scalars().all()

        if len(non_unique_fields) == 0:
            return True
        else:
            self._raise_user_unique_error(non_unique_fields)

    async def is_user_active(self, id: UserId) -> bool:
        async with self._get_read_session() as session:
            user = await session.get(User, id)
            if user:
                return user.is_active
            else:
                raise ValueError(f"User with id {id} does not exist")

    async def activate_user(self, username: Username) -> UserId:
        async with self._get_write_session() as session:
            query_result = await session.execute(
                select(User).where(User.username == username)
            )
            user = query_result.scalar_one_or_none()
            if user:
                if user.is_active:
                    raise ActivateUserError(f'User with username {username} is active')
                user.is_active = True
                return user.id
            else:
                raise ValueError(f"User with username {username} does not exist")

    async def verify_username_password(
        self, username: Username, password: str
    ) -> UserId:
        async with self._get_read_session() as session:
            stmt = (
                select(User)
                .where(
                    User.username == username,
                    User.is_active
                )
            )
            user = (await session.execute(stmt)).scalar_one_or_none()
            if user and user.check_password(password):
                return user.id
            else:
                raise InvalidCredentialsError('Invalid username or password')

    async def create_board(
        self, owner_id: UserId, name: str, description: Optional[str] = None
    ) -> BoardProtocol:
        async with self._get_write_session() as session:
            new_board = Board(
                id=get_id(),
                owner_id=owner_id,
                name=name,
                description=description
            )
            role = Role(
                id=get_id(),
                user_id=owner_id,
                board_id=new_board.id,
                role=UserRole.OWNER
            )
            session.add(new_board)
            session.add(role)
        return new_board

    async def get_board(self, board_id: UUID) -> BoardProtocol:
        async with self._get_read_session() as session:
            stmt = (
                select(Board)
                .where(Board.id == board_id)
                .options(
                    selectinload(Board.owner).load_only(
                        User.id,
                        User.username,
                        User.avatar,
                        User.first_name,
                        User.last_name
                    ),
                    selectinload(Board.columns).load_only(
                        Column.id,
                        Column.name,
                        Column.position,
                        Column.wip
                    ),
                    selectinload(Board.columns)
                    .selectinload(Column.tasks)
                    .load_only(
                        Task.id,
                        Task.name,
                        Task.description,
                        Task.priority,
                        Task.created_at,
                        Task.assignee_id,
                        Task.confirmed_by_id
                    ),
                    selectinload(Board.columns)
                    .selectinload(Column.tasks)
                    .selectinload(Task.assignee)
                    .load_only(
                        User.id,
                        User.username,
                        User.avatar,
                        User.first_name,
                        User.last_name
                    ),
                    selectinload(Board.columns)
                    .selectinload(Column.tasks)
                    .selectinload(Task.confirmed_by)
                    .load_only(
                        User.id,
                        User.username,
                        User.avatar,
                        User.first_name,
                        User.last_name
                    ),
                    selectinload(Board.columns)
                    .selectinload(Column.tasks)
                    .selectinload(Task.labels)
                    .load_only(Label.name, Label.color)
                )
            )
            board: Board = (
                await session.execute(stmt)
            ).scalars().unique().one_or_none()
        if not board:
            raise BoardNotFoundError(f'invalid id ({board_id})')

        return board

    async def is_user_in_board(self, user_id: UserId, board_id: UUID) -> bool:
        async with self._get_read_session() as session:
            stmt = select(
                exists().where(
                    and_(
                        Role.user_id == user_id,
                        Role.board_id == board_id
                    )
                )
            )
            result = await session.execute(stmt)
        return result.scalar()

    async def create_column(
        self, board_id: UUID, name: str, description: Optional[str], position: int,
        wip: int
    ) -> ColumnProtocol:
        async with self._get_write_session() as session:
            max_position = await session.scalar(
                select(func.count())
                .select_from(Column)
                .where(Column.board_id == board_id)
            )

            if position < 1 or position > max_position + 1:
                raise InvalidColumnPosition()
            new_column = Column(
                id=get_id(),
                board_id=board_id,
                name=name,
                description=description,
                position=position,
                wip=wip
            )
            await session.execute(
                update(Column)
                .where(
                    Column.board_id == board_id,
                    Column.position >= position
                )
                .values(position=Column.position + 1)
            )
            session.add(new_column)
        return new_column

    async def create_task(
        self, board_id: UUID, assign_id: UUID | None,
        confirmed_by_id: UUID | None, name: str, description: str,
        priority: TaskPriority, user_id: UserId
    ) -> TaskProtocol:
        async with self._get_read_session() as session:
            stmt = (
                select(Column.id)
                .where(Column.board_id == board_id)
                .order_by(Column.position.asc())
            )
            last_column = (await session.execute(stmt)).scalars().first()
            if not last_column:
                raise ColumnNotExist('The table has no columns')
        async with self._get_write_session() as session:
            new_task = Task(
                id=get_id(),
                board_id=board_id,
                column_id=last_column,
                assignee_id=assign_id,
                confirmed_by_id=confirmed_by_id,
                name=name,
                description=description,
                priority=priority
            )
            new_task_transition = TaskTransition(
                id=get_id(),
                task_id=new_task.id,
                user_id=user_id,
                column=last_column,
            )
            session.add(new_task)
            session.add(new_task_transition)
        return new_task

    async def get_user_role(self, user_id: UserId, board_id: UUID) -> UserRole:
        async with self._get_read_session() as session:
            stmt = select(Role.role).where(
                Role.user_id == user_id,
                Role.board_id == board_id
            )
            role = (await session.execute(stmt)).scalar_one_or_none()
            if not role:
                raise UserNotFoundError(
                    f'User {user_id} has no role in board {board_id}'
                )
            return role

    @asynccontextmanager
    async def _get_read_session(self) -> AsyncGenerator[AsyncSession, None]:
        def prevent_modifications(*args, **kwargs) -> NoReturn:  # noqa: ANN002
            raise DatabaseWriteError(
                'Modifications are not allowed in read-only session'
            )
        async with self.sessionmaker() as session:
            session: AsyncSession
            session.flush = prevent_modifications
            yield session

    @asynccontextmanager
    async def _get_write_session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self.sessionmaker() as session:
            session: AsyncSession
            try:
                yield session
                await session.commit()
            except SQLAlchemyError as e:
                await session.rollback()
                raise DatabaseError from e

    def _raise_user_unique_error(self, e: IntegrityError | Sequence) -> NoReturn:
        if isinstance(e, IntegrityError):
            constraint: str = getattr(e.orig, 'constraint_name')  # noqa: B009
            if constraint == 'username':
                raise UniqueUsernameError('Username is already taken') from e
            if constraint == 'email':
                raise UniqueEmailError('Email is already registered') from e
            raise e

        elif isinstance(e, Sequence):
            if 'username' in e:
                raise UniqueUsernameError('Username is already taken')
            if 'email' in e:
                raise UniqueEmailError('Email is already registered')
            raise ValueError('Error raised due to unknown fields in the sequence')

        raise ValueError('Argument e of unsupported type')
