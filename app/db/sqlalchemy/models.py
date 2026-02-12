# flake8-in-file-ignores: noqa: WPS110, WPS432

from datetime import datetime
from uuid import UUID

from passlib.context import CryptContext
from sqlalchemy import UUID as SAUUID
from sqlalchemy import Boolean, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import (ForeignKey, Index, Integer, String, UniqueConstraint,
                        func)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.db.abc.base import get_id
from app.db.enums import TaskPriority, UserRole
from app.types import UserId, Username

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


class Base(DeclarativeBase):
    pass


class ModelWithPassword(Base):
    __abstract__ = True

    _password: Mapped[str] = mapped_column(
        String(64), nullable=False, name='password'
    )

    def __init__(self, **kwargs) -> None:
        password = kwargs.pop('password', None)
        if password:
            self.password = password
        super().__init__(**kwargs)

    @hybrid_property
    def password(self) -> str:  # type: ignore[reportRedeclaration]
        return self._password

    @password.expression  # type: ignore[reportRedeclaration]
    def password(cls) -> str:  # type: ignore[reportRedeclaration]  # noqa: B902
        return cls._password

    @password.setter
    def password(self, value: str) -> None:
        self._password = pwd_context.hash(value)  # noqa: WPS60

    def is_password_hashed(self) -> bool:
        return pwd_context.identify(self._password) is not None

    def check_password(self, password: str) -> bool:
        return pwd_context.verify(password, self._password)


class User(ModelWithPassword):
    __tablename__ = 'users'

    id: Mapped[UserId] = mapped_column(
        SAUUID(as_uuid=True), primary_key=True, default=get_id
    )
    username: Mapped[Username] = mapped_column(
        String(24), unique=True, nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    first_name: Mapped[str] = mapped_column(String(48), nullable=False)
    last_name: Mapped[str] = mapped_column(String(48), nullable=False)
    avatar: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    boards: Mapped[list['Board']] = relationship(back_populates='owner')
    tasks: Mapped[list['Task']] = relationship(back_populates='assignee')
    comments: Mapped[list['Comment']] = relationship(back_populates='author')
    transitions: Mapped[list['TaskTransition']] = relationship(back_populates='user')
    roles: Mapped[list['Role']] = relationship(back_populates='user')


class Board(Base):
    __tablename__ = 'boards'

    id: Mapped[UUID] = mapped_column(
        SAUUID(as_uuid=True), primary_key=True, default=get_id
    )
    owner_id: Mapped[UserId] = mapped_column(
        SAUUID(as_uuid=True), ForeignKey('users.id'), nullable=False
    )
    name: Mapped[str] = mapped_column(String(24), nullable=False)
    description: Mapped[str | None] = mapped_column(String(4096))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    owner: Mapped['User'] = relationship(back_populates='boards')
    columns: Mapped[list['Column']] = relationship(back_populates='board')
    tasks: Mapped[list['Task']] = relationship(back_populates='board')
    labels: Mapped[list['Label']] = relationship(back_populates='board')
    roles: Mapped[list['Role']] = relationship(back_populates='board')


class Column(Base):
    __tablename__ = 'columns'
    __table_args__ = (
        UniqueConstraint('board_id', 'position', name='uq_board_position'),
    )

    id: Mapped[UUID] = mapped_column(
        SAUUID(as_uuid=True), primary_key=True, default=get_id
    )
    board_id: Mapped[UUID] = mapped_column(
        SAUUID(as_uuid=True), ForeignKey('boards.id'), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(24), nullable=False)
    description: Mapped[str | None] = mapped_column(String(4096))
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    wip: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    board: Mapped['Board'] = relationship(back_populates='columns')
    tasks: Mapped[list['Task']] = relationship(back_populates='column')
    transitions: Mapped[list['TaskTransition']] = relationship(back_populates='column')


class Task(Base):
    __tablename__ = 'tasks'

    id: Mapped[UUID] = mapped_column(
        SAUUID(as_uuid=True), primary_key=True, default=get_id
    )
    board_id: Mapped[UUID] = mapped_column(
        SAUUID(as_uuid=True), ForeignKey('boards.id'), nullable=False, index=True
    )
    column_id: Mapped[UUID] = mapped_column(
        SAUUID(as_uuid=True), ForeignKey('columns.id'), nullable=False
    )
    assignee_id: Mapped[UUID | None] = mapped_column(
        SAUUID(as_uuid=True), ForeignKey('users.id')
    )
    name: Mapped[str] = mapped_column(String(24), nullable=False)
    description: Mapped[str] = mapped_column(String(4096), nullable=False)
    priority: Mapped[TaskPriority] = mapped_column(
        SAEnum(TaskPriority, name='task_priority'),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    board: Mapped['Board'] = relationship(back_populates='tasks')
    column: Mapped['Column'] = relationship(back_populates='tasks')
    assignee: Mapped['User'] = relationship(back_populates='tasks')
    comments: Mapped[list['Comment']] = relationship(back_populates='task')
    transitions: Mapped[list['TaskTransition']] = relationship(back_populates='task')
    labels: Mapped[list['Label']] = relationship(
        secondary='tasks_labels',
        back_populates='tasks',
    )


class Label(Base):
    __tablename__ = 'labels'

    id: Mapped[UUID] = mapped_column(
        SAUUID(as_uuid=True), primary_key=True, default=get_id
    )
    board_id: Mapped[UUID] = mapped_column(
        SAUUID(as_uuid=True), ForeignKey('boards.id'), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(12), nullable=False)
    color: Mapped[str] = mapped_column(String(8), nullable=False)

    board: Mapped['Board'] = relationship(back_populates='labels')
    tasks: Mapped[list['Task']] = relationship(
        secondary='tasks_labels',
        back_populates='labels',
    )


class Comment(Base):
    __tablename__ = 'comments'

    id: Mapped[UUID] = mapped_column(
        SAUUID(as_uuid=True), primary_key=True, default=get_id
    )
    task_id: Mapped[UUID] = mapped_column(
        SAUUID(as_uuid=True), ForeignKey('tasks.id'), nullable=False, index=True
    )
    author_id: Mapped[UUID] = mapped_column(
        SAUUID(as_uuid=True), ForeignKey('users.id'), nullable=False
    )
    text: Mapped[str] = mapped_column(String(4096), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(),
    )

    task: Mapped['Task'] = relationship(back_populates='comments')
    author: Mapped['User'] = relationship(back_populates='comments')


class TaskTransition(Base):
    __tablename__ = 'task_transitions'

    id: Mapped[UUID] = mapped_column(
        SAUUID(as_uuid=True), primary_key=True, default=get_id
    )
    task_id: Mapped[UUID] = mapped_column(
        SAUUID(as_uuid=True), ForeignKey('tasks.id'), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        SAUUID(as_uuid=True), ForeignKey('users.id'), nullable=False
    )
    column_id: Mapped[UUID] = mapped_column(
        SAUUID(as_uuid=True), ForeignKey('columns.id'), nullable=False
    )
    moved_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    task: Mapped['Task'] = relationship(back_populates='transitions')
    user: Mapped['User'] = relationship(back_populates='transitions')
    column: Mapped['Column'] = relationship(back_populates='transitions')


class TaskLabel(Base):
    __tablename__ = 'tasks_labels'

    task: Mapped[UUID] = mapped_column(
        SAUUID(as_uuid=True),
        ForeignKey('tasks.id'),
        primary_key=True,
    )
    label: Mapped[UUID] = mapped_column(
        SAUUID(as_uuid=True),
        ForeignKey('labels.id'),
        primary_key=True,
    )


class Role(Base):
    __tablename__ = 'roles'
    __table_args__ = (
        Index('uq_roles_user_board', 'user_id', 'board_id', unique=True),
    )

    id: Mapped[UUID] = mapped_column(
        SAUUID(as_uuid=True), primary_key=True, default=get_id
    )
    user_id: Mapped[UserId] = mapped_column(
        SAUUID(as_uuid=True), ForeignKey('users.id'), nullable=False
    )
    board_id: Mapped[UUID] = mapped_column(
        SAUUID(as_uuid=True), ForeignKey('boards.id'), nullable=False
    )
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name='user_role'),
        nullable=False,
    )

    user: Mapped['User'] = relationship(back_populates='roles')
    board: Mapped['Board'] = relationship(back_populates='roles')
