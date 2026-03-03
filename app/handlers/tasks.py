# flake8-in-file-ignores: noqa: WPS110, WPS400

from litestar.handlers import get, patch, post
from litestar.openapi.spec import Example

from app import errors as error
from app import openapi_tags as tags
from app.config import DataBase, TaskConfig
from app.db.abc.base import str_to_id
from app.db.exc import ColumnNotExists, TaskNotExists
from app.errors import litestar_raise, litestar_response_spec
from app.handlers.controller import BaseController
from app.handlers.dto import (ColumnPreviewDTO,CommentDTO, ConfirmTaskDTO,
                              CreateCommentDTO, CreateTaskDTO,MoveTaskDTO,TaskDTO,
                              UserPreviewDTO, UserShortDTO)
from app.tokens.payloads import AccessTokenPayload


class TaskController(BaseController[TaskConfig]):
    config = TaskConfig()
    path = '/task'

    @post('/', responses={
        401: litestar_response_spec(examples=[
            Example('AccessTokenInvalid', value=error.AccessTokenInvalid()),
            Example('AccessTokenExpired', value=error.AccessTokenExpired()),
            Example('AuthorizationHeaderMissing', value=error.AuthorizationHeaderMissing())  # noqa
        ]),
        403: litestar_response_spec(examples=[
            Example('InsufficientRoleError', value=error.InsufficientRoleError()),
        ]),
        422: litestar_response_spec(examples=[
            Example('ColumnNotExist', value=error.ColumnNotExists())
        ])
    }, tags=[tags.task_handler])
    async def create_task(
        self, auth_client: AccessTokenPayload, db: DataBase, data: CreateTaskDTO
    ) -> TaskDTO:
        user_role = await db.get_user_role(
            user_id=auth_client.sub,
            board_id=data.board_id
        )
        if user_role < self.config.min_create_task_role:
            raise litestar_raise(error.InsufficientRoleError)

        try:
            task = await db.create_task(
                board_id=data.board_id,
                name=data.name,
                description=data.description,
                priority=data.priority,
                user_id=auth_client.sub,
                assign_id=None,
                confirmed_by_id=None
            )
        except ColumnNotExists as e:
            raise litestar_raise(error.ColumnNotExists) from e

        column = await db.get_column_name_position(task.column_id)
        return TaskDTO(
            id=task.id,
            board_id=task.board_id,
            name=task.name,
            description=task.description,
            priority=task.priority,
            created_at=task.created_at,
            column=ColumnPreviewDTO(
                name=column.name,
                position=column.position
            ),
            comments=[],
            assignee=None,
            confirmed_by=None
        )

    @get('/{task_id:str}', responses={
        401: litestar_response_spec(examples=[
            Example('AccessTokenInvalid', value=error.AccessTokenInvalid()),
            Example('AccessTokenExpired', value=error.AccessTokenExpired()),
            Example('AuthorizationHeaderMissing', value=error.AuthorizationHeaderMissing())  # noqa
        ]),
        422: litestar_response_spec(examples=[
            Example('ColumnNotExists', value=error.InvalidColumnPosition())
        ])
    }, tags=[tags.task_handler])
    async def get_task(
        self, auth_client: AccessTokenPayload, db: DataBase, task_id: str
    ) -> TaskDTO:
        try:
            valid_task_id = str_to_id(task_id)
        except ValueError as e:
            raise litestar_raise(error.ColumnNotExists) from e
        if not await db.is_user_in_board_by_task(auth_client.sub, valid_task_id):
            raise litestar_raise(error.UserNotInBoard)

        try:
            task = await db.get_task(valid_task_id)
        except TaskNotExists as e:
            raise litestar_raise(error.TaskNotExists) from e

        return TaskDTO(
            id=task.id,
            board_id=task.board_id,
            column=ColumnPreviewDTO(
                name=task.column.name,
                position=task.column.position
            ) if task.column else None,
            assignee=UserShortDTO(
                username=task.assignee.username,
                first_name=task.assignee.first_name,
                last_name=task.assignee.last_name,
                avatar=task.assignee.avatar
            ) if task.assignee else None,
            confirmed_by=UserShortDTO(
                username=task.confirmed_by.username,
                first_name=task.confirmed_by.first_name,
                last_name=task.confirmed_by.last_name,
                avatar=task.confirmed_by.avatar
            ) if task.confirmed_by else None,
            name=task.name,
            description=task.description,
            priority=task.priority,
            created_at=task.created_at,
            comments=[
                CommentDTO(
                    author=UserPreviewDTO(
                        username=comment.author.username,
                        avatar=comment.author.avatar
                    ),
                    text=comment.text,
                    created_at=comment.created_at
                ) for comment in task.comments
            ]
        )

    @post('/comment', responses={
        401: litestar_response_spec(examples=[
            Example('AccessTokenInvalid', value=error.AccessTokenInvalid()),
            Example('AccessTokenExpired', value=error.AccessTokenExpired()),
            Example('AuthorizationHeaderMissing', value=error.AuthorizationHeaderMissing())  # noqa
        ]),
        422: litestar_response_spec(examples=[
            Example('UserNotInBoard', value=error.UserNotInBoard())
        ])
    }, tags=[tags.task_handler])
    async def create_comment(
        self, auth_client: AccessTokenPayload, db: DataBase, data: CreateCommentDTO
    ) -> CommentDTO:
        if not await db.is_user_in_board_by_task(auth_client.sub, data.task_id):
            raise litestar_raise(error.UserNotInBoard)
        comment = await db.create_comment(
            task_id=data.task_id,
            author_id=auth_client.sub,
            text=data.text
        )
        author = await db.get_user_username_avatar(auth_client.sub)
        return CommentDTO(
            author=UserPreviewDTO(
                username=author.username,
                avatar=author.avatar
            ),
            text=comment.text,
            created_at=comment.created_at
        )

    @patch('/move', responses={
        401: litestar_response_spec(examples=[
            Example('AccessTokenInvalid', value=error.AccessTokenInvalid()),
            Example('AccessTokenExpired', value=error.AccessTokenExpired()),
            Example('AuthorizationHeaderMissing', value=error.AuthorizationHeaderMissing())  # noqa
        ]),
        403: litestar_response_spec(examples=[
            Example('TaskNotAssigneeError', value=error.TaskNotAssigneeError()),
        ]),
        422: litestar_response_spec(examples=[
            Example('TaskNotExists', value=error.TaskNotExists())
        ])
    }, tags=[tags.board_handler])
    async def move_task(
        self, auth_client: AccessTokenPayload, db: DataBase, data: MoveTaskDTO
    ) -> None:
        if not await db.is_users_task(auth_client.sub, data.task_id):
            raise litestar_raise(error.TaskNotAssigneeError)
        try:
            await db.task_transit(
                task_id=data.task_id,
                user_id=auth_client.sub,
                move_to=data.move_to
            )
        except TaskNotExists as e:
            raise litestar_raise(error.TaskNotExists) from e

    @patch('/confirm', responses={
        401: litestar_response_spec(examples=[
            Example('AccessTokenInvalid', value=error.AccessTokenInvalid()),
            Example('AccessTokenExpired', value=error.AccessTokenExpired()),
            Example('AuthorizationHeaderMissing', value=error.AuthorizationHeaderMissing())  # noqa
        ]),
        403: litestar_response_spec(examples=[
            Example('InsufficientRoleError', value=error.InsufficientRoleError()),
        ]),
        422: litestar_response_spec(examples=[
            Example('TaskNotExists', value=error.TaskNotExists())
        ])
    }, tags=[tags.task_handler])
    async def confirm_task(
        self, auth_client: AccessTokenPayload, db: DataBase, data: ConfirmTaskDTO
    ) -> None:
        try:
            board = await db.get_board_id_by_task(data.task_id)
        except TaskNotExists as e:
            raise litestar_raise(error.TaskNotExists) from e

        user_role = await db.get_user_role(
            user_id=auth_client.sub,
            board_id=board.id
        )
        if user_role < self.config.min_confirm_task_role:
            raise litestar_raise(error.InsufficientRoleError)

        await db.confirm_task(
            user_id=auth_client.sub,
            task_id=data.task_id
        )

