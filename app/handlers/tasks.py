# flake8-in-file-ignores: noqa: WPS110, WPS400

import json

from litestar.handlers import get, patch, post
from litestar.openapi.spec import Example

from app import errors as error
from app import openapi_tags as tags
from app.config import Cache, CacheKeys, DataBase, TaskConfig
from app.db.abc.base import str_to_id
from app.db.exc import ColumnNotExists, TaskNotExists
from app.errors import litestar_raise, litestar_response_spec
from app.handlers.controller import BaseController
from app.handlers.dto import (ColumnPreviewDTO, CommentDTO, ConfirmTaskDTO,
                              CreateCommentDTO, CreateTaskDTO, LabelDTO,
                              MoveTaskDTO, TaskDTO, UserPreviewDTO,
                              UserShortDTO, AssigneeTaskDTO)
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
            new_task = await db.create_task(
                board_id=data.board_id,
                name=data.name,
                description=data.description,
                priority=data.priority,
                user_id=auth_client.sub,
                assign_id=None,
                confirmed_by_id=None,
                label_ids=data.labels
            )
        except ColumnNotExists as e:
            raise litestar_raise(error.ColumnNotExists) from e

        task = await db.get_task(new_task.id)

        return TaskDTO(
            id=task.id,
            board_id=task.board_id,
            column=ColumnPreviewDTO(
                name=task.column.name,
                position=task.column.position
            ) if task.column else None,
            assignee=UserShortDTO(
                username=task.assignee.username,
                id=task.assignee.id,
                first_name=task.assignee.first_name,
                last_name=task.assignee.last_name,
                avatar=task.assignee.avatar
            ) if task.assignee else None,
            confirmed_by=UserShortDTO(
                id=task.confirmed_by.id,
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
                        id=comment.author.id,
                        username=comment.author.username,
                        avatar=comment.author.avatar
                    ),
                    text=comment.text,
                    created_at=comment.created_at
                ) for comment in task.comments
            ],
            labels=[
                LabelDTO(
                    id=label.id,
                    name=label.name,
                    color=label.color
                )
                for label in task.labels
            ],
            is_in_last_column=False
        )

    @get('/{task_id:str}', responses={
        401: litestar_response_spec(examples=[
            Example('AccessTokenInvalid', value=error.AccessTokenInvalid()),
            Example('AccessTokenExpired', value=error.AccessTokenExpired()),
            Example('AuthorizationHeaderMissing', value=error.AuthorizationHeaderMissing())  # noqa
        ]),
        422: litestar_response_spec(examples=[
            Example('TaskNotExists', value=error.TaskNotExists())
        ])
    }, tags=[tags.task_handler])
    async def get_task(
        self, auth_client: AccessTokenPayload, db: DataBase, cache: Cache,
        cache_keys: CacheKeys, task_id: str
    ) -> TaskDTO:
        try:
            valid_task_id = str_to_id(task_id)
        except ValueError as e:
            raise litestar_raise(error.TaskNotExists) from e

        task_from_cache = await cache.get(
            cache_keys.task.format(task_id)
        )
        if task_from_cache:
            return TaskDTO(**json.loads(task_from_cache))

        try:
            db_task = await db.get_task(valid_task_id)
        except TaskNotExists as e:
            raise litestar_raise(error.TaskNotExists) from e

        user_role = await db.get_user_role(
            user_id=auth_client.sub,
            board_id=db_task.board_id
        )
        if user_role < self.config.min_check_task_role:
            raise litestar_raise(error.InsufficientRoleError)

        if db_task.confirmed_by:
            is_in_last_column = False
        else:
            is_in_last_column = await db.is_task_in_last_column(
                db_task.id, db_task.board_id
            )

        task = TaskDTO(
            id=db_task.id,
            board_id=db_task.board_id,
            column=ColumnPreviewDTO(
                name=db_task.column.name,
                position=db_task.column.position
            ) if db_task.column else None,
            assignee=UserShortDTO(
                id=db_task.assignee.id,
                username=db_task.assignee.username,
                first_name=db_task.assignee.first_name,
                last_name=db_task.assignee.last_name,
                avatar=db_task.assignee.avatar
            ) if db_task.assignee else None,
            confirmed_by=UserShortDTO(
                id=db_task.confirmed_by.id,
                username=db_task.confirmed_by.username,
                first_name=db_task.confirmed_by.first_name,
                last_name=db_task.confirmed_by.last_name,
                avatar=db_task.confirmed_by.avatar
            ) if db_task.confirmed_by else None,
            name=db_task.name,
            description=db_task.description,
            priority=db_task.priority,
            created_at=db_task.created_at,
            comments=[
                CommentDTO(
                    author=UserPreviewDTO(
                        id=comment.author.id,
                        username=comment.author.username,
                        avatar=comment.author.avatar
                    ),
                    text=comment.text,
                    created_at=comment.created_at
                ) for comment in db_task.comments
            ],
            labels=[
                LabelDTO(
                    id=label.id,
                    name=label.name,
                    color=label.color
                )
                for label in db_task.labels
            ],
            is_in_last_column=is_in_last_column
        )

        await cache.set(
            cache_keys.task.format(task_id),
            json.dumps(task.model_dump(), default=str)
        )

        return task

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
        self, auth_client: AccessTokenPayload, db: DataBase, cache: Cache,
        cache_keys: CacheKeys, data: CreateCommentDTO
    ) -> CommentDTO:
        if not await db.is_user_in_board_by_task(auth_client.sub, data.task_id):
            raise litestar_raise(error.UserNotInBoard)
        comment = await db.create_comment(
            task_id=data.task_id,
            author_id=auth_client.sub,
            text=data.text
        )
        author = await db.get_user_username_avatar(auth_client.sub)

        await cache.del_key(
            cache_keys.task.format(data.task_id)
        )

        return CommentDTO(
            author=UserPreviewDTO(
                id=auth_client.sub,
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
        409: litestar_response_spec(examples=[
            Example('WIPLimit', value=error.WIPLimit()),
        ]),
        422: litestar_response_spec(examples=[
            Example('TaskNotExists', value=error.TaskNotExists()),
            Example('ColumnNotExists', value=error.ColumnNotExists())
        ])
    }, tags=[tags.task_handler])
    async def move_task(
        self, auth_client: AccessTokenPayload, db: DataBase, cache: Cache,
        cache_keys: CacheKeys, data: MoveTaskDTO
    ) -> None:
        if not await db.is_users_task(auth_client.sub, data.task_id):
            raise litestar_raise(error.TaskNotAssigneeError)

        try:
            if not await db.is_move_to_column_allowed_by_task(
                task_id=data.task_id,
                column_position=data.move_to
            ):
                raise litestar_raise(error.WIPLimit)
        except ColumnNotExists as e:
            raise litestar_raise(error.ColumnNotExists) from e

        try:
            await db.task_transit(
                task_id=data.task_id,
                user_id=auth_client.sub,
                move_to=data.move_to
            )
        except TaskNotExists as e:
            raise litestar_raise(error.TaskNotExists) from e
        except ColumnNotExists as e:
            raise litestar_raise(error.ColumnNotExists) from e

        board_id = await db.get_board_id_by_task(data.task_id)

        await cache.del_key(
            cache_keys.task.format(data.task_id)
        )

        await cache.del_key(
            cache_keys.board.format(board_id)
        )

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
            Example('TaskNotExists', value=error.TaskNotExists()),
            Example('TaskAlredyConfirmed', value=error.TaskAlredyConfirmed())
        ])
    }, tags=[tags.task_handler])
    async def confirm_task(
        self, auth_client: AccessTokenPayload, db: DataBase, cache: Cache,
        cache_keys: CacheKeys, data: ConfirmTaskDTO
    ) -> None:
        try:
            board_id = await db.get_board_id_by_task(data.task_id)
        except TaskNotExists as e:
            raise litestar_raise(error.TaskNotExists) from e

        user_role = await db.get_user_role(
            user_id=auth_client.sub,
            board_id=board_id
        )
        if user_role < self.config.min_confirm_task_role:
            raise litestar_raise(error.InsufficientRoleError)

        task = await db.get_task(data.task_id)
        if task.confirmed_by:
            raise litestar_raise(error.TaskAlredyConfirmed)

        await db.confirm_task(
            user_id=auth_client.sub,
            task_id=data.task_id
        )

        await cache.del_key(
            cache_keys.task.format(data.task_id)
        )

        await cache.del_key(
            cache_keys.tasks_confirmed.format(str(board_id))
        )

        await cache.del_key(
            cache_keys.board.format(str(board_id))
        )

    @patch('/assignee', responses={
        401: litestar_response_spec(examples=[
            Example('AccessTokenInvalid', value=error.AccessTokenInvalid()),
            Example('AccessTokenExpired', value=error.AccessTokenExpired()),
            Example('AuthorizationHeaderMissing', value=error.AuthorizationHeaderMissing())  # noqa
        ]),
        403: litestar_response_spec(examples=[
            Example('InsufficientRoleError', value=error.InsufficientRoleError()),
        ]),
        409: litestar_response_spec(examples=[
            Example('WIPLimit', value=error.WIPLimit()),
        ]),
        422: litestar_response_spec(examples=[
            Example('TaskNotExists', value=error.TaskNotExists()),
            Example('ColumnNotExists', value=error.ColumnNotExists()),
            Example('TaskAlredyAssignee', value=error.TaskAlredyAssignee())
        ])
    }, tags=[tags.task_handler])
    async def assignee_task(
        self, auth_client: AccessTokenPayload, db: DataBase, cache: Cache,
        cache_keys: CacheKeys, data: AssigneeTaskDTO
    ) -> None:
        try:
            board_id = await db.get_board_id_by_task(data.task_id)
        except TaskNotExists as e:
            raise litestar_raise(error.TaskNotExists) from e

        user_role = await db.get_user_role(
            user_id=auth_client.sub,
            board_id=board_id
        )
        if user_role < self.config.min_assignee_task_role:
            raise litestar_raise(error.InsufficientRoleError)

        task = await db.get_task(data.task_id)
        if task.assignee:
            raise litestar_raise(error.TaskAlredyAssignee)

        try:
            if not await db.is_move_to_column_allowed_by_task(
                task_id=task.id,
                column_position=1
            ):
                raise litestar_raise(error.WIPLimit)
        except ColumnNotExists as e:
            raise litestar_raise(error.ColumnNotExists) from e

        await db.assigne_task(
            user_id=auth_client.sub,
            task_id=data.task_id
        )

        await cache.del_key(
            cache_keys.task.format(data.task_id)
        )

        await cache.del_key(
            cache_keys.tasks_not_assigned.format(str(board_id))
        )

        await cache.del_key(
            cache_keys.board.format(str(board_id))
        )
