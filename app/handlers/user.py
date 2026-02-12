# flake8-in-file-ignores: noqa: B904, WPS110, WPS400

from litestar.handlers import get, patch, post
from litestar.openapi.spec import Example

from app import errors as error
from app import openapi_tags as tags
from app.config import (EMAIL_CHANGE_PASSWORD_BODY,
                        EMAIL_CHANGE_PASSWORD_SUBJECT, DataBase, Language,
                        Mailer, Token, TokenConfigType, UserConfig)
from app.db.exc import UserNotFoundError
from app.errors import litestar_raise, litestar_response_spec
from app.handlers.controller import BaseController
from app.handlers.dto import ChangeUserPasswordDTO, UserDTO
from app.mailers.base import NonExistentEmail
from app.tokens.base import (ChangePasswordTokenPayload, DecodeTokenError,
                             create_change_password_token,
                             verify_change_password_token)
from app.tokens.payloads import AccessTokenPayload
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
        self, db: DataBase, user_id: UserId
    ) -> UserDTO:
        try:
            user = await db.get_user(user_id)
            return UserDTO(
                id=user.id,
                username=user.username,
                email=user.email,
                is_active=user.is_active
            )
        except UserNotFoundError:
            raise litestar_raise(error.UserNotExists)

    @get('/username/{username:str}', responses={
        422: litestar_response_spec(examples=[
            Example('UserNotExists', value=error.UserNotExists())
        ])
    }, tags=[tags.user_handler])
    async def get_user_by_username(
        self, db: DataBase, username: Username
    ) -> UserDTO:
        try:
            user = await db.get_user_by_username(username)
            return UserDTO(
                id=user.id,
                username=user.username,
                email=user.email,
                is_active=user.is_active
            )
        except UserNotFoundError:
            raise litestar_raise(error.UserNotExists)

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
