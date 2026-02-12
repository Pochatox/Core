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
