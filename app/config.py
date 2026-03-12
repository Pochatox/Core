# flake8-in-file-ignores: noqa: WPS201

import logging
import os
from dataclasses import dataclass
from datetime import timedelta
from enum import Enum
from pathlib import Path
from types import MappingProxyType

from dotenv import load_dotenv
from kapusta import AlchemyCRUD
from litestar.config.cors import CORSConfig
from litestar.logging import LoggingConfig
from litestar.openapi import OpenAPIConfig
from litestar.openapi.plugins import SwaggerRenderPlugin

from app.caches.base import RedisAsyncCache
from app.caches.configs import RedisConfig
from app.db.enums import UserRole
from app.db.sqlalchemy.base import AsyncSQLAlchemyDB
from app.db.sqlalchemy.config import SQLAlchemyDBConfig
from app.mailers.base import AsyncSMTPMailer
from app.mailers.configs import SMTPConfig
from app.task_managers.base import KapustaTaskManager
from app.task_managers.configs import KapustaConfig
from app.tokens.base import JWToken
from app.tokens.configs import JWTokenConfig

SERVICE_NAME = 'Pochatox-Core'
VERSION = '0.0.0'


class Language(Enum):
    ru = 'ru'
    en = 'en'


APP_PATH = Path(__file__).parent
ROOT_PATH = APP_PATH.parent

load_dotenv(ROOT_PATH / '.env')

cors_config = CORSConfig(
    allow_origins=os.getenv('ALLOW_ORIGINS').split(',')  # type: ignore
)

logging_config = LoggingConfig(
    root={
        'level': 'DEBUG',
        'handlers': ['file']
    },
    handlers={
        'file': {
            'class': 'logging.FileHandler',
            'filename': ROOT_PATH / f"{SERVICE_NAME}.log",
            'mode': 'w',
            'formatter': 'standard',
        }
    },
    formatters={
        'standard': {
            'format': ('%(name)s | %(levelname)s | %(asctime)s'
                       ' | %(module)s | %(funcName)s | %(message)s'),
            'datefmt': '%Y-%m-%d %H:%M:%S'
        }
    },
    log_exceptions='always',
)

openapi_config = OpenAPIConfig(
    title=f'{SERVICE_NAME} API',
    version=VERSION,
    render_plugins=[
        SwaggerRenderPlugin()
    ]
)

MAIL_URL: str = os.getenv('MAIL_URL')  # type: ignore

DATABASE_URL: str = os.getenv('DATABASE_URL')  # type: ignore

_db_logger = logging.getLogger('sqlalchemy.engine')
_db_logger.setLevel(logging.INFO)
DataBase = AsyncSQLAlchemyDB
DataBaseConfig = SQLAlchemyDBConfig(
    logger=_db_logger,
    db_url=DATABASE_URL,
    session_maker_kwargs={'expire_on_commit': False}
)

Cache = RedisAsyncCache
CacheConfig = RedisConfig(
    logger=logging.getLogger('redis'),
    redis_host=os.getenv('REDIS_HOST'),  # type: ignore
    redis_port=int(os.getenv('REDIS_PORT'))  # type: ignore
)


@dataclass(frozen=True)
class CacheKeys:
    user_by_id: str = 'user_id: {}'
    user_by_username: str = 'user_un: {}'
    user_short: str = 'user_sh: {}'
    user_role_in_board: str = 'user_rl: {}'
    user_role_in_board_by_task: str = 'user_rlbt: {}'
    users_list: str = 'users_lt: {}'

    board: str = 'board: {}'
    boards: str = 'boards: {}'

    tasks_confirmed: str = 'c_tasks: {}'
    tasks_not_assigned: str = 'na_tasks: {}'
    task_transitions: str = 't_trans: {}'
    task: str = 'task: {}'


Mailer = AsyncSMTPMailer
MailerConfig = SMTPConfig(
    logger=logging.getLogger('smtp'),
    self_email=os.getenv('SELF_EMAIL'),  # type: ignore
    smtp_server=os.getenv('EMAIL_SERVER'),  # type: ignore
    smtp_user=os.getenv('EMAIL_USER'),  # type: ignore
    smtp_password=os.getenv('EMAIL_PASSWORD'),  # type: ignore
    smtp_port=int(os.getenv('SMTP_PORT'))  # type: ignore
)

Token = JWToken
TokenConfigType = JWTokenConfig
TokenConfig = TokenConfigType(
    logger=logging.getLogger('tokens'),
    alg=os.getenv('JWT_ALGORITHM'),  # type: ignore
    typ='JWT',
    key=os.getenv('JWT_KEY'),  # type: ignore
)

TaskManager = KapustaTaskManager
TaskManagerConfig = KapustaConfig(
    logger=logging.getLogger('kapusta'),
    crud=AlchemyCRUD(DATABASE_URL),
    max_tick_interval=5 * 60,
    default_overdue_time_delta=None,
    default_max_retry_attempts=3,
    default_timeout=0
)


@dataclass(frozen=True)
class BaseConfig:
    ...


@dataclass(frozen=True)
class AuthConfig(BaseConfig):
    username_min_length: int = 2
    username_max_length: int = 12
    email_max_length: int = 256
    password_min_length: int = 5
    password_max_length: int = 74

    registration_token_exp: timedelta = timedelta(minutes=5)
    access_token_exp: timedelta = timedelta(hours=8)
    refresh_token_exp: timedelta = timedelta(weeks=5)

    del_inactive_user_after: timedelta = timedelta(minutes=5)


@dataclass(frozen=True)
class UserConfig(BaseConfig):
    change_password_token_exp: timedelta = timedelta(minutes=5)
    invite_token_exp: timedelta = timedelta(days=1)

    min_invite_role: UserRole = UserRole.OWNER


@dataclass(frozen=True)
class BoardConfig(BaseConfig):
    min_create_column_role = UserRole.OWNER
    min_delete_user_role: UserRole = UserRole.OWNER
    min_create_label_role = UserRole.MEMBER
    min_task_transitions_role = UserRole.MEMBER
    min_create_maintainer_role = UserRole.OWNER
    min_name_length = 3
    max_name_length = 24
    min_column_name = 3
    max_column_name = 24
    max_label_name = 12
    max_description_length = 4096


@dataclass(frozen=True)
class TaskConfig(BaseConfig):
    min_create_task_role = UserRole.MAINTAINER
    min_check_task_role = UserRole.MEMBER
    min_assignee_task_role = UserRole.MEMBER
    min_confirm_task_role = UserRole.MAINTAINER
    min_name_length = 3
    max_name_length = 24
    max_comment_length = 4096
    max_description_length = 4096


EMAIL_REGISTRATION_SUBJECT = MappingProxyType({
    Language.en: 'Pochatox: Registration',
    Language.ru: 'Pochatox: Регистрация'
})

EMAIL_REGISTRATION_BODY = MappingProxyType({
    Language.en: (
        'To confirm your registration, visit '
        + MAIL_URL + '/auth/verify-email/{}\n'
        'Use the link within 5 minutes. Do not share it with anyone.'
    ),
    Language.ru: (
        'Для подтверждения регистрации перейдите по ссылке '
        + MAIL_URL + '/auth/verify-email/{}\n'
        'Перейдите по ссылке в течении 5 минут. Никому не передавайте её.'
    )
})

EMAIL_CHANGE_PASSWORD_SUBJECT = MappingProxyType({
    Language.en: 'Pochatox: Change password',
    Language.ru: 'Pochatox: Смена пароля'
})

EMAIL_CHANGE_PASSWORD_BODY = MappingProxyType({
    Language.en: (
        'To reset your password, visit '
        + MAIL_URL + '/user/change-password/{}\n'
        'Use the link within 5 minutes.'
    ),
    Language.ru: (
        'Для смены пароля перейдите по ссылке '
        + MAIL_URL + '/user/change-password/{}\n'
        'Перейдите по ссылке в течении 5 минут.'
    )
})

EMAIL_INVITE_SUBJECT = MappingProxyType({
    Language.en: 'Pochatox: Project Invitation',
    Language.ru: 'Pochatox: Приглашение в проект'
})

EMAIL_INVITE_BODY = MappingProxyType({
    Language.en: (
        'User {first_name} {last_name} (@{username}) invites you to the project '
        '{board_name} (created at {board_created_at})'
        + MAIL_URL + '/user/invite{token}\n'
        'To accept the invitation, follow the link within 24 hours'
    ),
    Language.ru: (
        'Пользователь {first_name} {last_name} (@{username}) приглашает вас в проект'
        '{board_name} (создан {board_created_at})'
        + MAIL_URL + '/user/invite{token}\n'
        'Для принятия приглашения перейдите по ссылке в течении 24 часов'
    )
})
