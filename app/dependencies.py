# flake8-in-file-ignores: noqa: B904

from litestar.connection import Request

from app import errors as error
from app.config import Language
from app.errors import litestar_raise
from app.tokens.base import (BaseToken, BaseTokenConfig, DecodeTokenError,
                             TokenExpiredError)
from app.tokens.payloads import AccessTokenPayload


def get_language(request: Request) -> Language:
    lang = request.cookies.get('language', Language.en.value)
    try:
        lang = Language(lang)
    except ValueError:
        lang = Language.en
    return lang


def auth_client(
    request: Request, token_type: type[BaseToken], token_config: BaseTokenConfig
) -> AccessTokenPayload:
    try:
        access_token = token_type.decode(
            token=request.headers['Authorization'].split(' ', 1)[1],
            config=token_config,
            payload_type=AccessTokenPayload
        )

    except TokenExpiredError:
        raise litestar_raise(error.AccessTokenExpired)

    except (DecodeTokenError, IndexError):
        raise litestar_raise(error.AccessTokenInvalid)

    except KeyError:
        raise litestar_raise(error.AuthorizationHeaderMissing)

    return access_token.payload  # type: ignore
