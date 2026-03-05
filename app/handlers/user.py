# flake8-in-file-ignores: noqa: B904, WPS110, WPS400

import json

from litestar.handlers import get, patch, post
from litestar.openapi.spec import Example

from app import errors as error
from app import openapi_tags as tags
from app.config import (EMAIL_CHANGE_PASSWORD_BODY,
                        EMAIL_CHANGE_PASSWORD_SUBJECT, Cache, CacheKeys,
                        DataBase, Language, Mailer, Token, TokenConfigType,
                        UserConfig)
from app.db.enums import UserRole
from app.db.exc import UserNotFoundError
from app.errors import litestar_raise, litestar_response_spec
from app.handlers.controller import BaseController
from app.handlers.dto import (BoardShortDTO, ChangeUserPasswordDTO, InviteDTO,
                              UserDTO, UserShortDTO)
from app.mailers.base import NonExistentEmail
from app.tokens.base import (ChangePasswordTokenPayload, DecodeTokenError,
                             create_change_password_token, create_invite_token,
                             verify_change_password_token, verify_invite_token)
from app.tokens.payloads import AccessTokenPayload, InviteTokenPayload
from app.types import UserId, Username


class UserController(BaseController[UserConfig]):
    config = UserConfig()
    path = '/user'

    @get('/id/{user_id:str}', responses={
        422: litestar_response_spec(examples=[
            Example('UserNotExists', value=error.UserNotExists())
        ])
    }, tags=[tags.user_handler])
    async def get_user_by_id(
        self, db: DataBase, user_id: UserId, cache: Cache, cache_keys: CacheKeys
    ) -> UserDTO:
        user_from_cache = await cache.get(
            cache_keys.user_by_id.format(user_id)
        )
        if user_from_cache:
            return UserDTO(**json.loads(user_from_cache))

        try:
            db_user = await db.get_user(user_id)
        except UserNotFoundError:
            raise litestar_raise(error.UserNotExists)
        user = UserDTO(
            id=db_user.id,
            username=db_user.username,
            email=db_user.email,
            is_active=db_user.is_active,
            first_name=db_user.first_name,
            last_name=db_user.last_name,
            avatar=db_user.avatar,
            created_at=db_user.created_at
        )

        await cache.set(
            cache_keys.user_by_id.format(user_id),
            json.dumps(user.model_dump(), default=str)
        )

        return user

    @get('/username/{username:str}', responses={
        422: litestar_response_spec(examples=[
            Example('UserNotExists', value=error.UserNotExists())
        ])
    }, tags=[tags.user_handler])
    async def get_user_by_username(
        self, db: DataBase, username: Username, cache: Cache, cache_keys: CacheKeys
    ) -> UserDTO:
        user_from_cache = await cache.get(
            cache_keys.user_by_username.format(username)
        )
        if user_from_cache:
            return UserDTO(**json.loads((user_from_cache)))

        try:
            db_user = await db.get_user_by_username(username)
        except UserNotFoundError:
            raise litestar_raise(error.UserNotExists)
        user = UserDTO(
            id=db_user.id,
            username=db_user.username,
            email=db_user.email,
            is_active=db_user.is_active,
            first_name=db_user.first_name,
            last_name=db_user.last_name,
            avatar=db_user.avatar,
            created_at=db_user.created_at
        )

        await cache.set(
            cache_keys.user_by_username.format(username),
            json.dumps(user.model_dump(), default=str)
        )

        return user

    @post('/change-password-request', responses={
        401: litestar_response_spec(examples=[
            Example('AccessTokenInvalid', value=error.AccessTokenInvalid()),
            Example('AccessTokenExpired', value=error.AccessTokenExpired()),
            Example('AuthorizationHeaderMissing', value=error.AuthorizationHeaderMissing())  # noqa
        ]),
        422: litestar_response_spec(examples=[
            Example('UserNotExists', value=error.UserNotExists()),
            Example('EmailNonExistent', value=error.EmailNonExists())
        ])
    }, tags=[tags.user_handler])
    async def change_password_request(
        self, auth_client: AccessTokenPayload, db: DataBase, mailer: Mailer,
        lang: Language, token_type: type[Token], token_config: TokenConfigType
    ) -> None:
        try:
            user_email = await db.get_user_email(auth_client.sub)
        except UserNotFoundError:
            raise litestar_raise(error.UserNotExists)

        change_password_token = create_change_password_token(
            token_type=token_type,
            token_config=token_config,
            exp=self.config.change_password_token_exp,
            sub=auth_client.sub
        )

        try:
            await mailer.send(
                subject=EMAIL_CHANGE_PASSWORD_SUBJECT[lang],
                body=EMAIL_CHANGE_PASSWORD_BODY[lang].format(
                    change_password_token.encode()
                ),
                to_email=user_email
            )
        except NonExistentEmail:
            raise litestar_raise(error.EmailNonExists)

    @patch('change-password/{change_password_token:str}', responses={
        401: litestar_response_spec(examples=[
            Example('AccessTokenInvalid', value=error.AccessTokenInvalid()),
            Example('AccessTokenExpired', value=error.AccessTokenExpired()),
            Example('AuthorizationHeaderMissing', value=error.AuthorizationHeaderMissing())  # noqa
        ]),
        403: litestar_response_spec(examples=[
            Example('TokensSubjectNotEqual', value=error.TokensSubjectNotEqual())  # noqa: E501
        ]),
        422: litestar_response_spec(examples=[
            Example('ChangePasswordTokenInvalid', value=error.ChangePasswordTokenInvalid())  # noqa
        ])
    }, tags=[tags.user_handler])
    async def change_password(
        self, auth_client: AccessTokenPayload, db: DataBase, token_type: type[Token],
        token_config: TokenConfigType, data: ChangeUserPasswordDTO,
        change_password_token: str
    ) -> None:
        try:
            encode_change_password_token = verify_change_password_token(
                token=change_password_token,
                token_type=token_type,
                token_config=token_config
            )
            change_password_token_payload: ChangePasswordTokenPayload = (
                encode_change_password_token.payload
            )  # type: ignore
        except DecodeTokenError:
            raise litestar_raise(error.ChangePasswordTokenInvalid)

        if auth_client.sub != change_password_token_payload.sub:
            raise litestar_raise(error.TokensSubjectNotEqual)

        await db.change_user_password(
            id=auth_client.sub,
            new_password=data.password
        )

    @post('/invite-request', responses={
        401: litestar_response_spec(examples=[
            Example('AccessTokenInvalid', value=error.AccessTokenInvalid()),
            Example('AccessTokenExpired', value=error.AccessTokenExpired()),
            Example('AuthorizationHeaderMissing', value=error.AuthorizationHeaderMissing())  # noqa
        ]),
        403: litestar_response_spec(examples=[
            Example('UserNotInBoard', value=error.UserNotInBoard()),
            Example('InsufficientRoleError', value=error.InsufficientRoleError())
        ]),
        422: litestar_response_spec(examples=[
            Example('UserNotExists', value=error.UserNotExists()),
            Example('BoardNotExists', value=error.BoardNotExists()),
            Example('EmailNonExistent', value=error.EmailNonExists())
        ])
    }, tags=[tags.user_handler])
    async def invite_request(
        self, auth_client: AccessTokenPayload, db: DataBase, mailer: Mailer,
        lang: Language, token_type: type[Token], token_config: TokenConfigType,
        data: InviteDTO
    ) -> None:
        try:
            user_role = await db.get_user_role(
                user_id=auth_client.sub,
                board_id=data.board_id
            )
        except UserNotFoundError as e:
            raise litestar_raise(error.UserNotInBoard) from e
        if user_role < self.config.min_invite_role:
            raise litestar_raise(error.InsufficientRoleError)

        try:
            invited_email = await db.get_user_email(data.invited_id)
        except UserNotFoundError:
            raise litestar_raise(error.UserNotExists)

        invite_token = create_invite_token(
            token_type=token_type,
            token_config=token_config,
            exp=self.config.change_password_token_exp,
            invited=data.invited_id,
            board=data.board_id
        )

        user = await db.get_user_names(auth_client.sub)
        board = await db.get_board_name_created_at(data.board_id)
        if not board:
            raise litestar_raise(error.BoardNotExists)

        try:
            await mailer.send(
                subject=EMAIL_CHANGE_PASSWORD_SUBJECT[lang],
                body=EMAIL_CHANGE_PASSWORD_BODY[lang].format(
                    first_name=user.first_name,
                    last_name=user.last_name,
                    username=user.username,
                    board_name=board.name,
                    board_created_at=board.created_at,
                    token=invite_token
                ),
                to_email=invited_email
            )
        except NonExistentEmail:
            raise litestar_raise(error.EmailNonExists)

    @get('invite/{invite_token:str}', responses={
        401: litestar_response_spec(examples=[
            Example('AccessTokenInvalid', value=error.AccessTokenInvalid()),
            Example('AccessTokenExpired', value=error.AccessTokenExpired()),
            Example('AuthorizationHeaderMissing', value=error.AuthorizationHeaderMissing())  # noqa
        ]),
        403: litestar_response_spec(examples=[
            Example('TokensSubjectNotEqual', value=error.TokensSubjectNotEqual())  # noqa: E501
        ]),
        422: litestar_response_spec(examples=[
            Example('InviteTokenInvalid', value=error.InviteTokenInvalid())  # noqa
        ])
    }, tags=[tags.user_handler])
    async def invite(
        self, auth_client: AccessTokenPayload, db: DataBase, token_type: type[Token],
        token_config: TokenConfigType, invite_token: str
    ) -> None:
        try:
            encode_invite_token = verify_invite_token(
                token=invite_token,
                token_type=token_type,
                token_config=token_config
            )
            invite_token_payload: InviteTokenPayload = (
                encode_invite_token.payload
            )  # type: ignore
        except DecodeTokenError:
            raise litestar_raise(error.InviteTokenInvalid)

        if auth_client.sub != invite_token_payload.invited:
            raise litestar_raise(error.TokensSubjectNotEqual)

        await db.create_role(
            user_id=auth_client.sub,
            board_id=invite_token_payload.board,
            role=UserRole.MEMBER
        )

    @get('/boards', responses={
        401: litestar_response_spec(examples=[
            Example('AccessTokenInvalid', value=error.AccessTokenInvalid()),
            Example('AccessTokenExpired', value=error.AccessTokenExpired()),
            Example('AuthorizationHeaderMissing', value=error.AuthorizationHeaderMissing())  # noqa
        ])
    }, tags=[tags.user_handler])
    async def get_boards(
        self, auth_client: AccessTokenPayload, db: DataBase, cache: Cache,
        cache_keys: CacheKeys
    ) -> list[BoardShortDTO]:
        boards_from_cache = await cache.get(
            cache_keys.boards.format(auth_client.sub)
        )
        if boards_from_cache:
            return json.loads(boards_from_cache)

        boards_with_roles = await db.get_users_boards(
            user_id=auth_client.sub,
        )
        boards = [
            BoardShortDTO(
                id=board.id,
                owner=UserShortDTO(
                    username=board.owner.username,
                    first_name=board.owner.first_name,
                    last_name=board.owner.last_name,
                    avatar=board.owner.avatar,
                ),
                name=board.name,
                description=board.description,
                created_at=board.created_at,
                user_role=role,
            )
            for board, role in boards_with_roles
        ]

        await cache.set(
            cache_keys.boards.format(auth_client.sub),
            json.dumps([board.model_dump() for board in boards], default=str)
        )

        return boards
