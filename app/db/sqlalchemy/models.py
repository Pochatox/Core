# flake8-in-file-ignores: noqa: WPS110, WPS432

from passlib.context import CryptContext
from sqlalchemy import String
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


class PasswordHashingError(Exception): ...


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
