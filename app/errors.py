# flake8-in-file-ignores: noqa: WPS432

from http import HTTPStatus
from typing import Any, Mapping

from litestar.exceptions import HTTPException
from litestar.openapi.datastructures import ResponseSpec
from litestar.openapi.spec import Example
from pydantic import BaseModel

from app.types import Sentinel


class BaseError(BaseModel):
    status_code: int = 400
    detail: str = ''
    extra: dict = {}

###
# miss-X: Error codes for missing required elements
###


class AuthorizationHeaderMissing(BaseError):
    status_code: int = 401
    detail: str = HTTPStatus(401).phrase
    extra: dict = {
        'error_code': 'miss-1',
        'message': 'Authorization header missing'
    }


class RefreshTokenHeaderMissing(BaseError):
    status_code: int = 401
    detail: str = HTTPStatus(401).phrase
    extra: dict = {
        'error_code': 'miss-2',
        'message': 'Refresh token missing in header'
    }


###
# inv-X: Error codes for invalid inputs or tokens
###


class RegistrationTokenInvalid(BaseError):
    status_code: int = 422
    detail: str = HTTPStatus(422).phrase
    extra: dict = {
        'error_code': 'inv-1',
        'message': 'Registration token is invalid'
    }


class AccessTokenInvalid(BaseError):
    status_code: int = 401
    detail: str = HTTPStatus(401).phrase
    extra: dict = {
        'error_code': 'inv-2',
        'message': 'Access token is invalid'
    }


class RefreshTokenInvalid(BaseError):
    status_code: int = 401
    detail: str = HTTPStatus(401).phrase
    extra: dict = {
        'error_code': 'inv-3',
        'message': 'Refresh token is invalid'
    }


class ChangePasswordTokenInvalid(BaseError):
    status_code: int = 422
    detail: str = HTTPStatus(422).phrase
    extra: dict = {
        'error_code': 'inv-4',
        'message': 'Change password token is invalid'
    }


class InviteTokenInvalid(BaseError):
    status_code: int = 422
    detail: str = HTTPStatus(422).phrase
    extra: dict = {
        'error_code': 'inv-4',
        'message': 'Invite token is invalid'
    }

###
# uniq-X: Error codes for uniqueness violations
###


class UsernameNotUnique(BaseError):
    status_code: int = 409
    detail: str = HTTPStatus(409).phrase
    extra: dict = {
        'error_code': 'uniq-1',
        'message': 'Username not unique'
    }


class EmailNotUnique(BaseError):
    status_code: int = 409
    detail: str = HTTPStatus(409).phrase
    extra: dict = {
        'error_code': 'uniq-2',
        'message': 'Email not unique'
    }


###
# exist-X: Error codes for non-existent entities
###

class EmailNonExists(BaseError):
    status_code: int = 422
    detail: str = HTTPStatus(422).phrase
    extra: dict = {
        'error_code': 'exist-1',
        'message': 'Email does not exist'
    }


class UserNotExists(BaseError):
    status_code: int = 422
    detail: str = HTTPStatus(422).phrase
    extra: dict = {
        'error_code': 'exist-2',
        'message': 'User not exists'
    }


class BoardNotExists(BaseError):
    status_code: int = 422
    detail: str = HTTPStatus(422).phrase
    extra: dict = {
        'error_code': 'exist-3',
        'message': 'The board does not exist'
    }


class InvalidColumnPosition(BaseError):
    status_code: int = 422
    detail: str = HTTPStatus(422).phrase
    extra: dict = {
        'error_code': 'exist-4',
        'message': 'The column does not exist'
    }


class ColumnNotExists(BaseError):
    status_code: int = 422
    detail: str = HTTPStatus(422).phrase
    extra: dict = {
        'error_code': 'exist-5',
        'message': 'The column does not exist'
    }


class TaskNotExists(BaseError):
    status_code: int = 422
    detail: str = HTTPStatus(422).phrase
    extra: dict = {
        'error_code': 'exist-6',
        'message': 'The task does not exist'
    }

###
# exp-X: Error codes for expired tokens
###


class AccessTokenExpired(BaseError):
    status_code: int = 401
    detail: str = HTTPStatus(401).phrase
    extra: dict = {
        'error_code': 'exp-1',
        'message': 'Access token expired'
    }


class RefreshTokenExpired(BaseError):
    status_code: int = 401
    detail: str = HTTPStatus(401).phrase
    extra: dict = {
        'error_code': 'exp-2',
        'message': 'Refresh token expired'
    }

###
# access-X: Error codes for access restrictions
###


class UserNotInBoard(BaseError):
    status_code: int = 403
    detail: str = HTTPStatus(403).phrase
    extra: dict = {
        'error_code': 'access-1',
        'message': 'The user does not have access to the board'
    }


class InsufficientRoleError(BaseError):
    status_code: int = 403
    detail: str = HTTPStatus(403).phrase
    extra: dict = {
        'error_code': 'access-2',
        'message': 'The user has an insufficient role'
    }


class TaskNotAssigneeError(BaseError):
    status_code: int = 403
    detail: str = HTTPStatus(403).phrase
    extra: dict = {
        'error_code': 'access-3',
        'message': 'The user is not the assignee of this task'
    }

###
# other-X: Error codes for other types of errors
###


class UserIsActive(BaseError):
    status_code: int = 403
    detail: str = HTTPStatus(403).phrase
    extra: dict = {
        'error_code': 'other-1',
        'message': 'The user is already active'
    }


class InvalidCredentials(BaseError):
    status_code: int = 401
    detail: str = HTTPStatus(401).phrase
    extra: dict = {
        'error_code': 'other-2',
        'message': 'Invalid credentials'
    }


class TokensSubjectNotEqual(BaseError):
    status_code: int = 403
    detail: str = HTTPStatus(403).phrase
    extra: dict = {
        'error_code': 'other-3',
        'message': 'Tokens subject not equal'
    }


class WIPLimit(BaseError):
    status_code: int = 409
    detail: str = HTTPStatus(409).phrase
    extra: dict = {
        'error_code': 'other-5',
        'message': 'The WIP limit has been reached in the column'
    }


def litestar_raise(
    error_model: type[BaseError], add_to_extra: Mapping[str, Any] = Sentinel,
    headers: dict[str, str] = Sentinel
) -> HTTPException:
    error_instance = error_model()
    return HTTPException(
        status_code=error_instance.status_code,
        detail=error_instance.detail,
        extra=({**error_instance.extra, **add_to_extra}
               if add_to_extra is not Sentinel else error_instance.extra),
        headers=headers if headers is not Sentinel else None,
    )


def litestar_response_spec(examples: list[Example]) -> ResponseSpec:
    return ResponseSpec(
        data_container=BaseError,
        description='errors',
        examples=examples
    )
