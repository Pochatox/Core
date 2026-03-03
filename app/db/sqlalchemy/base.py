# flake8-in-file-ignores: noqa: WPS110, WPS204, WPS203, WPS615, WPS221
# pyright: reportReturnType=false

from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncGenerator, Literal, NoReturn, Optional, Sequence
from uuid import UUID

from sqlalchemy import and_, case, delete, exists, func, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)
from sqlalchemy.orm import load_only, selectinload

from app.db.abc.base import BaseAsyncDB, get_id
from app.db.abc.models import (BoardProtocol, ColumnProtocol, CommentProtocol,
                               LabelProtocol, RoleProtocol, TaskProtocol,
                               TaskTransitionProtocol, UserProtocol)
from app.db.enums import TaskPriority, UserRole
from app.db.exc import (ActivateUserError, BoardNotFoundError, ColumnNotExists,
                        DatabaseError, InvalidColumnPosition,
                        InvalidCredentialsError, TaskNotExists,
                        UniqueEmailError, UniqueUsernameError,
                        UserNotFoundError)
from app.db.sqlalchemy.config import SQLAlchemyDBConfig
from app.db.sqlalchemy.models import (Base, Board, Column, Comment, Label,
                                      Role, Task, TaskTransition, User)
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
                    selectinload(Board.labels).load_only(
                        Label.id,
                        Label.name,
                        Label.color
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
                        User.username,
                        User.avatar,
                    ),
                    selectinload(Board.columns)
                    .selectinload(Column.tasks)
                    .selectinload(Task.confirmed_by)
                    .load_only(
                        User.username,
                        User.avatar,
                    ),
                    selectinload(Board.columns)
                    .selectinload(Column.tasks)
                    .selectinload(Task.labels)
                    .load_only(Label.name, Label.color)
                )
            )
            board = (
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
        return bool(result.scalar())

    async def is_user_in_board_by_column(
        self, user_id: UserId, column_id: UUID
    ) -> bool:
        async with self._get_read_session() as session:
            stmt = select(
                exists().where(
                    and_(
                        Role.user_id == user_id,
                        Role.board_id == select(Column.board_id).where(
                            Column.id == column_id
                        ).scalar_subquery()
                    )
                )
            )
            result = await session.execute(stmt)
        return bool(result.scalar())

    async def is_user_in_board_by_task(self, user_id: UserId, task_id: UUID) -> bool:
        async with self._get_read_session() as session:
            stmt = select(
                exists().where(
                    and_(
                        Role.user_id == user_id,
                        Role.board_id == select(Task.board_id).where(
                            Task.id == task_id
                        ).scalar_subquery()
                    )
                )
            )
            result = await session.execute(stmt)
        return bool(result.scalar())

    async def create_column(
        self, board_id: UUID, name: str, description: Optional[str], position: int,
        wip: int
    ) -> ColumnProtocol:
        async with self._get_write_session() as session:
            max_position = await session.scalar(
                select(func.count())
                .select_from(Column)
                .where(Column.board_id == board_id)
            ) or 0

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

    async def create_comment(
        self, task_id: UUID, author_id: UUID, text: str
    ) -> CommentProtocol:
        async with self._get_write_session() as session:
            new_comment = Comment(
                id=get_id(),
                task_id=task_id,
                author_id=author_id,
                text=text
            )
            session.add(new_comment)
        return new_comment

    async def create_task(
        self, board_id: UUID, assign_id: UUID | None,
        confirmed_by_id: UUID | None, name: str, description: str,
        priority: TaskPriority, user_id: UserId
    ) -> TaskProtocol:
        async with self._get_write_session() as session:
            new_task = Task(
                id=get_id(),
                board_id=board_id,
                column_id=None,
                assignee_id=assign_id,
                confirmed_by_id=confirmed_by_id,
                name=name,
                description=description,
                priority=priority
            )
            session.add(new_task)
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

    async def get_column(self, column_id: UUID) -> ColumnProtocol:
        async with self._get_read_session() as session:
            stmt = (
                select(Column)
                .where(Column.id == column_id)
                .options(
                    selectinload(Column.tasks)
                    .load_only(
                        Task.id,
                        Task.name,
                        Task.description,
                        Task.priority,
                        Task.created_at,
                        Task.assignee_id,
                        Task.confirmed_by_id
                    ),
                    selectinload(Column.tasks)
                    .selectinload(Task.assignee)
                    .load_only(
                        User.username,
                        User.avatar,
                    ),
                    selectinload(Column.tasks)
                    .selectinload(Task.confirmed_by)
                    .load_only(
                        User.username,
                        User.avatar,
                    ),
                    selectinload(Column.tasks)
                    .selectinload(Task.labels)
                    .load_only(Label.name, Label.color)
                )
            )
            column = (
                await session.execute(stmt)
            ).scalars().unique().one_or_none()
        if not column:
            raise ColumnNotExists(f'Column with id {column_id} is not found')
        return column

    async def get_task(self, task_id: UUID) -> TaskProtocol:
        async with self._get_read_session() as session:
            stmt = (
                select(Task)
                .where(Task.id == task_id)
                .options(
                    selectinload(Task.assignee).load_only(
                        User.username,
                        User.avatar,
                        User.first_name,
                        User.last_name
                    ),
                    selectinload(Task.confirmed_by).load_only(
                        User.username,
                        User.avatar,
                        User.first_name,
                        User.last_name
                    ),
                    selectinload(Task.labels).load_only(
                        Label.name,
                        Label.color
                    ),
                    selectinload(Task.comments).load_only(
                        Comment.text,
                        Comment.created_at
                    ).selectinload(Comment.author).load_only(
                        User.username,
                        User.avatar
                    ),
                    selectinload(Task.column).load_only(
                        Column.name,
                        Column.position
                    )
                )
            )
            task = (await session.execute(stmt)).scalars().unique().one_or_none()
        if not task:
            raise TaskNotExists(f'Task with id {task_id} is not found')
        return task

    async def get_user_username_avatar(self, user_id: UUID) -> UserProtocol:
        async with self._get_read_session() as session:
            stmt = select(
                User.username,
                User.avatar
            ).where(User.id == user_id)
            username_avatar = (await session.execute(stmt)).scalar_one_or_none()
            if not username_avatar:
                raise UserNotFoundError(f'User with id {user_id} is not found')
            return username_avatar

    async def get_column_name_position(self, column_id: UUID) -> ColumnProtocol:
        async with self._get_read_session() as session:
            stmt = select(
                Column.name,
                Column.position
            ).where(Column.id == column_id)
            result = (await session.execute(stmt)).one_or_none()
            if not result:
                raise ColumnNotExists(f'Column with id {column_id} is not found')
            return result

    async def create_label(
        self, board_id: UUID, name: str, color: str
    ) -> LabelProtocol:
        async with self._get_write_session() as session:
            new_label = Label(
                id=get_id(),
                board_id=board_id,
                name=name,
                color=color
            )
            session.add(new_label)
        return new_label

    async def task_transit(
        self, task_id: UUID, user_id: UserId, move_to: int
    ) -> None:
        async with self._get_read_session() as session:
            stmt = (
                select(Column.id)
                .join(Task, Task.board_id == Column.board_id)
                .where(Task.id == task_id, Column.position == move_to)
            )
            column_id = (await session.execute(stmt)).scalars().first()
            if not column_id:
                raise TaskNotExists('Task not exists')
        async with self._get_write_session() as session:
            task_transition = TaskTransition(
                id=get_id(),
                task_id=task_id,
                user_id=user_id,
                column=column_id
            )
            session.add(task_transition)
        return task_transition

    async def is_users_task(self, user_id: UserId, task_id: UUID) -> bool:
        async with self._get_read_session() as session:
            stmt = select(
                exists().where(
                    and_(
                        Task.id == task_id,
                        Task.assignee_id == user_id
                    )
                )
            )
            result = await session.execute(stmt)
        return bool(result.scalar())

    async def confirm_task(self, user_id: UserId, task_id: UUID) -> None:
        async with self._get_write_session() as session:
            result = await session.execute(
                update(Task)
                .where(Task.id == task_id)
                .values(
                    confirmed_by_id=user_id,
                    column_id=None,
                )
            )
            if result.rowcount == 0:  # type: ignore
                raise TaskNotExists(f'Task with id {task_id} is not found')

    async def get_board_id_by_task(self, task_id: UUID) -> BoardProtocol:
        async with self._get_read_session() as session:
            stmt = select(Task.board_id).where(Task.id == task_id)
            board_id = (await session.execute(stmt)).scalar_one_or_none()
            if not board_id:
                raise TaskNotExists(f'Task with id {task_id} is not found')
            return board_id

    async def get_confirmed_tasks(self, board_id: UUID) -> list[TaskProtocol]:
        async with self._get_read_session() as session:
            result = await session.execute(
                select(Task)
                .where(
                    Task.board_id == board_id,
                    Task.confirmed_by_id.is_not(None),
                )
                .options(
                    load_only(
                        Task.name,
                        Task.description,
                        Task.priority,
                        Task.created_at,
                    ),
                    selectinload(Task.assignee).load_only(
                        User.username,
                        User.avatar,
                    ),
                    selectinload(Task.confirmed_by).load_only(
                        User.username,
                        User.avatar,
                    ),
                    selectinload(Task.labels).load_only(
                        Label.name,
                        Label.color,
                    ),
                )
            )
        return result.scalars().all()

    async def get_task_transitions(
        self, board_id: UUID
    ) -> list[TaskTransitionProtocol]:
        async with self._get_read_session() as session:
            result = await session.execute(
                select(TaskTransition)
                .join(Task, Task.id == TaskTransition.task_id)
                .where(Task.board_id == board_id)
                .options(
                    load_only(TaskTransition.moved_at),
                    selectinload(TaskTransition.task).load_only(
                        Task.name,
                        Task.priority,
                        Task.created_at,
                    ).selectinload(Task.assignee).load_only(
                        User.username,
                        User.avatar,
                    ),
                    selectinload(TaskTransition.task).selectinload(
                        Task.confirmed_by
                    ).load_only(
                        User.username,
                        User.avatar,
                    ),
                    selectinload(TaskTransition.user).load_only(
                        User.username,
                        User.avatar,
                    ),
                    selectinload(TaskTransition.column).load_only(
                        Column.name,
                        Column.position,
                    ),
                )
            )
        return result.scalars().all()

    async def get_user_names(self, user_id: UserId) -> UserProtocol:
        async with self._get_read_session() as session:
            stmt = select(
                User.first_name,
                User.last_name,
                User.username
            ).where(User.id == user_id)
            result = (await session.execute(stmt)).one_or_none()
            if not result:
                raise UserNotFoundError(f'User with id {user_id} is not found')
            return result

    async def get_board_name_created_at(self, board_id: UUID) -> BoardProtocol:
        async with self._get_read_session() as session:
            stmt = select(
                Board.name,
                Board.created_at
            ).where(Board.id == board_id)
            result = (await session.execute(stmt)).one_or_none()
            if not result:
                raise BoardNotFoundError(f'Board with id {board_id} is not found')
            return result

    async def create_role(
        self, user_id: UserId, board_id: UUID, role: UserRole
    ) -> RoleProtocol:
        async with self._get_write_session() as session:
            new_role = Role(
                id=get_id(),
                user_id=user_id,
                board_id=board_id,
                role=role
            )
            session.add(new_role)
        return new_role

    async def is_move_to_column_allowed_by_task(
        self, task_id: UUID, column_position: int,
    ) -> bool:
        async with self._get_read_session() as session:
            result = await session.scalar(
                select(
                    Column.wip > (
                        func.count(Task.id)
                        - func.count().filter(Task.id == task_id)
                    )
                )
                .select_from(Task)
                .join(Column, Column.board_id == Task.board_id)
                .outerjoin(
                    Task,
                    (Task.column_id == Column.id)
                )
                .where(
                    Task.id == task_id,
                    Column.position == column_position,
                )
                .group_by(Column.wip)
            )
            if result is None:
                raise ColumnNotExists(
                    f'Column with position {column_position} is not found'
                )
        return result

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
