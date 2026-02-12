# flake8-in-file-ignores: noqa: WPS432

"""This module defines a collection of error models.

### Error Models
The error models inherit from the `BaseError` class and represent various types
    of errors that can occur in the application.

Each error model includes:
- `status_code`: The HTTP status code associated with the error.
- `detail`: A brief description of the HTTP status.
- `extra`: A dictionary containing additional information, including:
    - `error_code`: A unique identifier for the error.
    - `message`: A human-readable description of the error.

The error codes are categorized into groups based on their nature, such as:
- Missing required elements (`miss-X`).
- Invalid inputs or tokens (`inv-X`).
- Uniqueness violations (`uniq-X`).
- Non-existent entities (`exist-X`).
- Expired tokens (`exp-X`).
- Other errors (`other-X`).

### Utility Functions
1. `litestar_raise`:
     A helper function to raise an `HTTPException` using a specified error model.
     It allows adding custom headers or additional data to the error's `extra` field.
     Example usage:
     ```python
     raise litestar_raise(error.EmailNotUnique)
     ```
2. `litestar_response_spec`:
     A helper function to generate a `ResponseSpec` for documenting API responses
        in OpenAPI.
     It accepts a list of `Example` objects to provide example error responses
        for specific HTTP status codes.
     Example usage:
     ```python
     @post('/registration', responses={
             409: litestar_response_spec(examples=[
                     Example('UsernameNotUnique', value=error.UsernameNotUnique()),
                     Example('EmailNotUnique', value=error.EmailNotUnique())
             ])
     })
     ```

These utilities streamline error handling and improve API documentation by providing
    consistent error structures and examples.
"""

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
        'error_code': 'exist-3',
        'message': 'User not exists'
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
        'error_code': 'other-4',
        'message': 'Tokens subject not equal'
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
