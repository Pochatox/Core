from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Generic, Self, TypeVar

import jwt

from app.tokens.configs import BaseTokenConfig, JWTokenConfig
from app.tokens.payloads import (AccessTokenPayload, BaseTokenPayload,
                                 ChangePasswordTokenPayload,
                                 RefreshTokenPayload, RegistrationTokenPayload)
from app.types import UserId, Username


class TokenError(Exception): ...
class EncodeTokenError(TokenError): ...
class DecodeTokenError(TokenError): ...
class TokenExpiredError(DecodeTokenError): ...


TokenConfig = TypeVar('TokenConfig', bound=BaseTokenConfig)
PayloadType = TypeVar('PayloadType', bound=BaseTokenPayload)
TokenType = TypeVar('TokenType', bound='BaseToken')


@dataclass
class BaseToken(ABC, Generic[TokenConfig]):
    payload: BaseTokenPayload
    config: TokenConfig

    @abstractmethod
    def encode(self) -> str: ...

    @classmethod
    @abstractmethod
    def decode(cls, token: str, config: TokenConfig,
               payload_type: type[PayloadType]) -> Self: ...


@dataclass
class JWToken(BaseToken[JWTokenConfig]):

    def encode(self) -> str:
        try:
            payload = self.payload.model_dump()
            token = jwt.encode(
                payload=payload,
                key=self.config.key,
                algorithm=self.config.alg,
                headers={
                    'alg': self.config.alg,
                    'typ': self.config.typ
                },
                json_encoder=self.config.json_encoder,
                sort_headers=self.config.sort_headers
            )
            self.config.logger.debug('The token is encoded with the'
                                     f' payload: {payload}')
            return token
        except Exception as e:
            self.config.logger.debug('token encode error')
            raise EncodeTokenError from e

    @classmethod
    def decode(
        cls, token: str, config: JWTokenConfig, payload_type: type[PayloadType]
    ) -> Self:
        try:
            token_payload = payload_type(
                **jwt.decode(
                    jwt=token,
                    key=config.key,
                    algorithms=config.alg
                )
            )
            return cls(
                payload=token_payload,
                config=config
            )

        except jwt.ExpiredSignatureError as e:
            raise TokenExpiredError from e

        except Exception as e:
            raise DecodeTokenError from e


def create_registration_token(
    token_type: type[TokenType], token_config: BaseTokenConfig, exp: timedelta,
    sub: Username
) -> TokenType:
    registration_token_payload = RegistrationTokenPayload(
        exp=int((datetime.now(UTC) + exp).timestamp()),
        sub=sub,
    )
    return token_type(
        registration_token_payload,
        token_config
    )


def create_access_token(
    token_type: type[TokenType], token_config: BaseTokenConfig, exp: timedelta,
    sub: UserId
) -> TokenType:
    access_token_payload = AccessTokenPayload(
        exp=(datetime.now() + exp).timestamp(),
        sub=sub
    )
    return token_type(
        access_token_payload,
        token_config
    )


def create_refresh_token(
    token_type: type[TokenType], token_config: BaseTokenConfig, exp: timedelta,
    sub: UserId
) -> TokenType:
    refresh_token_payload = RefreshTokenPayload(
        exp=(datetime.now() + exp).timestamp(),
        sub=sub
    )
    return token_type(
        refresh_token_payload,
        token_config
    )


def create_change_password_token(
    token_type: type[TokenType], token_config: BaseTokenConfig, exp: timedelta,
    sub: UserId
) -> TokenType:
    refresh_token_payload = ChangePasswordTokenPayload(
        exp=(datetime.now() + exp).timestamp(),
        sub=sub
    )
    return token_type(
        refresh_token_payload,
        token_config
    )


def verify_access_token(
    token: str, token_type: type[TokenType], token_config: BaseTokenConfig
) -> TokenType:
    try:
        return token_type.decode(
            token, token_config, AccessTokenPayload
        )
    except DecodeTokenError as e:
        raise e


def verify_refresh_token(
    token: str, token_type: type[TokenType], token_config: BaseTokenConfig
) -> TokenType:
    try:
        return token_type.decode(
            token, token_config, RefreshTokenPayload
        )
    except DecodeTokenError as e:
        raise e


def verify_registration_token(
    token: str, token_type: type[TokenType], token_config: BaseTokenConfig
) -> TokenType:
    try:
        return token_type.decode(
            token, token_config, RegistrationTokenPayload
        )
    except DecodeTokenError as e:
        raise e


def verify_change_password_token(
    token: str, token_type: type[TokenType], token_config: BaseTokenConfig
) -> TokenType:
    try:
        return token_type.decode(
            token, token_config, ChangePasswordTokenPayload
        )
    except DecodeTokenError as e:
        raise e
