# flake8-in-file-ignores: noqa: WPS110, WPS400


import json

from litestar.handlers import get, post
from litestar.openapi.spec import Example

from app import errors as error
from app import openapi_tags as tags
from app.config import BoardConfig, Cache, CacheKeys, DataBase
from app.db.abc.base import str_to_id
from app.db.enums import UserRole
from app.db.exc import ColumnNotExists, TaskNotExists, UserNotFoundError
from app.errors import litestar_raise, litestar_response_spec
from app.handlers.controller import BaseController
from app.handlers.dto import (BoardDTO, ColumnDTO, ColumnPreviewDTO,
                              ColumnShortDTO, CreateBoardDTO, CreateColumnDTO,
                              CreateLabelDTO, LabelDTO, ShortTaskDTO,
                              TaskPreviewDTO, TaskTransitionDTO,
                              UserPreviewDTO, UserShortDTO)
from app.tokens.payloads import AccessTokenPayload


class BoardController(BaseController[BoardConfig]):
    config = BoardConfig()
    path = '/board'

    @post('/', responses={
        401: litestar_response_spec(examples=[
            Example('AccessTokenInvalid', value=error.AccessTokenInvalid()),
            Example('AccessTokenExpired', value=error.AccessTokenExpired()),
            Example('AuthorizationHeaderMissing', value=error.AuthorizationHeaderMissing())  # noqa
        ])
    }, tags=[tags.board_handler])
    async def create_board(
        self, auth_client: AccessTokenPayload, db: DataBase, data: CreateBoardDTO
    ) -> BoardDTO:
        board = await db.create_board(
            owner_id=auth_client.sub,
            name=data.name,
            description=data.description
        )
        user = await db.get_short_user(board.owner_id)
        return BoardDTO(
            id=board.id,
            owner=UserShortDTO(
                id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                avatar=user.avatar
            ),
            name=board.name,
            description=board.description,
            created_at=board.created_at,
            columns=[],
            labels=[]
        )

    @get('/{board_id:str}', responses={
        401: litestar_response_spec(examples=[
            Example('AccessTokenInvalid', value=error.AccessTokenInvalid()),
            Example('AccessTokenExpired', value=error.AccessTokenExpired()),
            Example('AuthorizationHeaderMissing', value=error.AuthorizationHeaderMissing())  # noqa
        ]),
        403: litestar_response_spec(examples=[
            Example('UserNotInBoard', value=error.UserNotInBoard())
        ]),
        422: litestar_response_spec(examples=[
            Example('BoardNotExists', value=error.BoardNotExists())
        ])
    }, tags=[tags.board_handler])
    async def get_board(
        self, auth_client: AccessTokenPayload, db: DataBase, cache: Cache,
        cache_keys: CacheKeys, board_id: str
    ) -> BoardDTO:
        try:
            board_valid_id = str_to_id(board_id)
        except ValueError as e:
            raise litestar_raise(error.BoardNotExists) from e
        if not await db.is_user_in_board(auth_client.sub, board_valid_id):
            raise litestar_raise(error.UserNotInBoard)

        board_from_cache = await cache.get(
            cache_keys.board.format(board_id)
        )
        if board_from_cache:
            return BoardDTO(**json.loads(board_from_cache))

        db_board = await db.get_board(board_valid_id)
        board = BoardDTO(
            id=db_board.id,
            owner=UserShortDTO(
                id=db_board.owner.id,
                username=db_board.owner.username,
                first_name=db_board.owner.first_name,
                last_name=db_board.owner.last_name,
                avatar=db_board.owner.avatar
            ),
            name=db_board.name,
            description=db_board.description,
            created_at=db_board.created_at,
            columns=[
                ColumnShortDTO(
                    name=column.name,
                    position=column.position,
                    wip=column.wip,
                    tasks=[
                        ShortTaskDTO(
                            id=task.id,
                            assignee=UserPreviewDTO(
                                id=task.assignee.id,
                                username=task.assignee.username,
                                avatar=task.assignee.avatar
                            ) if task.assignee else None,
                            confirmed_by=UserPreviewDTO(
                                id=task.confirmed_by.id,
                                username=task.confirmed_by.username,
                                avatar=task.confirmed_by.avatar
                            ) if task.confirmed_by else None,
                            name=task.name,
                            description=task.description,
                            priority=task.priority,
                            created_at=task.created_at,
                            labels=[
                                LabelDTO(
                                    id=label.id,
                                    name=label.name,
                                    color=label.color
                                )
                                for label in task.labels
                            ]
                        )
                        for task in column.tasks
                    ]
                )
                for column in db_board.columns
            ],
            labels=[
                LabelDTO(
                    id=label.id,
                    name=label.name,
                    color=label.color
                ) for label in db_board.labels
            ]
        )
        await cache.set(
            cache_keys.board.format(board_id),
            json.dumps(board.model_dump(), default=str)
        )
        return board

    @post('/column', responses={
        401: litestar_response_spec(examples=[
            Example('AccessTokenInvalid', value=error.AccessTokenInvalid()),
            Example('AccessTokenExpired', value=error.AccessTokenExpired()),
            Example('AuthorizationHeaderMissing', value=error.AuthorizationHeaderMissing())  # noqa
        ]),
        403: litestar_response_spec(examples=[
            Example('InsufficientRoleError', value=error.InsufficientRoleError()),
        ]),
        422: litestar_response_spec(examples=[
            Example('InvalidColumnPosition', value=error.InvalidColumnPosition()),
            Example('UserNotExists', value=error.UserNotExists())
        ])
    }, tags=[tags.board_handler])
    async def create_column(
        self, auth_client: AccessTokenPayload, db: DataBase, cache: Cache,
        cache_keys: CacheKeys, data: CreateColumnDTO
    ) -> ColumnDTO:
        try:
            user_role = await db.get_user_role(
                user_id=auth_client.sub,
                board_id=data.board_id
            )
        except UserNotFoundError as e:
            raise litestar_raise(error.UserNotExists) from e
        if user_role < self.config.min_create_column_role:
            raise litestar_raise(error.InsufficientRoleError)

        try:
            column = await db.create_column(
                board_id=data.board_id,
                name=data.name,
                description=data.description,
                wip=data.wip,
                position=data.position
            )
        except ColumnNotExists as e:
            raise litestar_raise(error.InvalidColumnPosition) from e

        await cache.del_key(
            cache_keys.board.format(data.board_id)
        )

        return ColumnDTO(
            id=column.id,
            board_id=column.board_id,
            name=column.name,
            description=column.description,
            position=column.position,
            wip=column.wip,
            created_at=column.created_at,
            tasks=[]
        )

    @get('/column/{column_id:str}', responses={
        401: litestar_response_spec(examples=[
            Example('AccessTokenInvalid', value=error.AccessTokenInvalid()),
            Example('AccessTokenExpired', value=error.AccessTokenExpired()),
            Example('AuthorizationHeaderMissing', value=error.AuthorizationHeaderMissing())  # noqa
        ]),
        403: litestar_response_spec(examples=[
            Example('UserNotInBoard', value=error.UserNotInBoard()),
        ]),
        422: litestar_response_spec(examples=[
            Example('ColumnNotExists', value=error.ColumnNotExists())
        ])
    }, tags=[tags.board_handler])
    async def get_column(
        self, auth_client: AccessTokenPayload, db: DataBase, cache: Cache,
        cache_keys: CacheKeys, column_id: str
    ) -> ColumnDTO:
        try:
            valid_column_id = str_to_id(column_id)
        except ValueError as e:
            raise litestar_raise(error.ColumnNotExists) from e
        if not await db.is_user_in_board_by_column(auth_client.sub, valid_column_id):
            raise litestar_raise(error.UserNotInBoard)

        column_from_cache = await cache.get(
            cache_keys.column.format(column_id)
        )

        if column_from_cache:
            return ColumnDTO(**json.loads(column_from_cache))

        try:
            db_column = await db.get_column(valid_column_id)
        except ColumnNotExists as e:
            raise litestar_raise(error.ColumnNotExists) from e

        column = ColumnDTO(
            id=db_column.id,
            board_id=db_column.board_id,
            name=db_column.name,
            description=db_column.description,
            position=db_column.position,
            wip=db_column.wip,
            created_at=db_column.created_at,
            tasks=[
                ShortTaskDTO(
                    id=task.id,
                    assignee=UserPreviewDTO(
                        id=task.assignee.id,
                        username=task.assignee.username,
                        avatar=task.assignee.avatar
                    ) if task.assignee else None,
                    confirmed_by=UserPreviewDTO(
                        id=task.confirmed_by.id,
                        username=task.confirmed_by.username,
                        avatar=task.confirmed_by.avatar
                    ) if task.confirmed_by else None,
                    name=task.name,
                    description=task.description,
                    priority=task.priority,
                    created_at=task.created_at,
                    labels=[
                        LabelDTO(
                            id=label.id,
                            name=label.name,
                            color=label.color
                        )
                        for label in task.labels
                    ]
                )
                for task in db_column.tasks
            ]
        )

        await cache.set(
            cache_keys.column.format(column_id),
            json.dumps(column.model_dump(), default=str)
        )

        return column

    @post('/label', responses={
        401: litestar_response_spec(examples=[
            Example('AccessTokenInvalid', value=error.AccessTokenInvalid()),
            Example('AccessTokenExpired', value=error.AccessTokenExpired()),
            Example('AuthorizationHeaderMissing', value=error.AuthorizationHeaderMissing())  # noqa
        ]),
        422: litestar_response_spec(examples=[
            Example('ColumnNotExists', value=error.ColumnNotExists())
        ])
    }, tags=[tags.board_handler])
    async def create_label(
        self, auth_client: AccessTokenPayload, db: DataBase, cache: Cache,
        cache_keys: CacheKeys, data: CreateLabelDTO
    ) -> LabelDTO:
        user_role = await db.get_user_role(
            user_id=auth_client.sub,
            board_id=data.board_id
        )
        if user_role < self.config.min_create_label_role:
            raise litestar_raise(error.InsufficientRoleError)

        label = await db.create_label(
            board_id=data.board_id,
            name=data.name,
            color=data.color
        )

        await cache.del_key(
            cache_keys.board.format(data.board_id)
        )

        return LabelDTO(
            id=label.id,
            name=label.name,
            color=label.color
        )

    @get('/{board_id:str}/confirmed-tasks', responses={
        401: litestar_response_spec(examples=[
            Example('AccessTokenInvalid', value=error.AccessTokenInvalid()),
            Example('AccessTokenExpired', value=error.AccessTokenExpired()),
            Example('AuthorizationHeaderMissing', value=error.AuthorizationHeaderMissing())  # noqa
        ]),
        403: litestar_response_spec(examples=[
            Example('UserNotInBoard', value=error.UserNotInBoard()),
        ]),
        422: litestar_response_spec(examples=[
            Example('BoardNotExists', value=error.BoardNotExists())
        ])
    }, tags=[tags.board_handler])
    async def get_confirmed_tasks(
        self, auth_client: AccessTokenPayload, db: DataBase, cache: Cache,
        cache_keys: CacheKeys, board_id: str
    ) -> list[ShortTaskDTO]:
        try:
            valid_board_id = str_to_id(board_id)
        except ValueError as e:
            raise litestar_raise(error.BoardNotExists) from e
        if not await db.is_user_in_board(auth_client.sub, valid_board_id):
            raise litestar_raise(error.UserNotInBoard)

        tasks_from_cache = await cache.get(
            cache_keys.tasks_confirmed.format(board_id)
        )
        if tasks_from_cache:
            return json.loads(tasks_from_cache)

        db_tasks = await db.get_confirmed_tasks(valid_board_id)
        tasks = [
            ShortTaskDTO(
                id=task.id,
                assignee=UserPreviewDTO(
                    id=task.assignee.id,
                    username=task.assignee.username,
                    avatar=task.assignee.avatar
                ) if task.assignee else None,
                confirmed_by=UserPreviewDTO(
                    id=task.confirmed_by.id,
                    username=task.confirmed_by.username,
                    avatar=task.confirmed_by.avatar
                ) if task.confirmed_by else None,
                name=task.name,
                description=task.description,
                priority=task.priority,
                created_at=task.created_at,
                labels=[
                    LabelDTO(
                        id=label.id,
                        name=label.name,
                        color=label.color
                    )
                    for label in task.labels
                ]
            ) for task in db_tasks
        ]

        await cache.set(
            cache_keys.tasks_confirmed.format(board_id),
            json.dumps([task.model_dump() for task in tasks], default=str)
        )

        return tasks

    @get('/{board_id:str}/task-transitions', responses={
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
            Example('BoardNotExists', value=error.BoardNotExists())
        ])
    }, tags=[tags.board_handler])
    async def get_task_transitions(
        self, auth_client: AccessTokenPayload, db: DataBase, cache: Cache,
        cache_keys: CacheKeys, board_id: str
    ) -> list[TaskTransitionDTO]:
        try:
            valid_board_id = str_to_id(board_id)
        except ValueError as e:
            raise litestar_raise(error.BoardNotExists) from e

        try:
            user_role = await db.get_user_role(
                user_id=auth_client.sub,
                board_id=valid_board_id
            )
        except UserNotFoundError as e:
            raise litestar_raise(error.UserNotInBoard) from e
        if user_role < self.config.min_task_transitions_role:
            raise litestar_raise(error.InsufficientRoleError)

        task_transitions_from_cache = await cache.get(
            cache_keys.task_transitions.format(board_id)
        )

        if task_transitions_from_cache:
            return json.loads(task_transitions_from_cache)

        db_task_transitions = await db.get_task_transitions(valid_board_id)
        task_transitions = [
            TaskTransitionDTO(
                task=TaskPreviewDTO(
                    assignee=UserPreviewDTO(
                        id=tt.task.assignee.id,
                        username=tt.task.assignee.username,
                        avatar=tt.task.assignee.avatar,
                    ) if tt.task.assignee else None,
                    confirmed_by=UserPreviewDTO(
                        id=tt.task.confirmed_by.id,
                        username=tt.task.confirmed_by.username,
                        avatar=tt.task.confirmed_by.avatar,
                    ) if tt.task.confirmed_by else None,
                    name=tt.task.name,
                    priority=tt.task.priority,
                    created_at=tt.task.created_at,
                ),
                user=UserPreviewDTO(
                    id=tt.user.id,
                    username=tt.user.username,
                    avatar=tt.user.avatar,
                ),
                column=ColumnPreviewDTO(
                    name=tt.column.name,
                    position=tt.column.position,
                ),
                moved_at=tt.moved_at,
            )
            for tt in db_task_transitions
        ]

        await cache.set(
            cache_keys.task_transitions.format(board_id),
            json.dumps(
                [task_transition.model_dump()
                 for task_transition in task_transitions], default=str
            )
        )

        return task_transitions

    @get('/{board_id:str}/not-assigned-tasks', responses={
        401: litestar_response_spec(examples=[
            Example('AccessTokenInvalid', value=error.AccessTokenInvalid()),
            Example('AccessTokenExpired', value=error.AccessTokenExpired()),
            Example('AuthorizationHeaderMissing', value=error.AuthorizationHeaderMissing())  # noqa
        ]),
        403: litestar_response_spec(examples=[
            Example('UserNotInBoard', value=error.UserNotInBoard()),
        ]),
        422: litestar_response_spec(examples=[
            Example('BoardNotExists', value=error.BoardNotExists())
        ])
    }, tags=[tags.board_handler])
    async def get_not_assigned_tasks(
        self, auth_client: AccessTokenPayload, db: DataBase, cache: Cache,
        cache_keys: CacheKeys, board_id: str
    ) -> list[ShortTaskDTO]:
        try:
            valid_board_id = str_to_id(board_id)
        except ValueError as e:
            raise litestar_raise(error.BoardNotExists) from e
        if not await db.is_user_in_board(auth_client.sub, valid_board_id):
            raise litestar_raise(error.UserNotInBoard)

        tasks_from_cache = await cache.get(
            cache_keys.tasks_not_assigned.format(board_id)
        )
        if tasks_from_cache:
            return json.loads(tasks_from_cache)

        db_tasks = await db.get_not_assigned_tasks(valid_board_id)
        tasks = [
            ShortTaskDTO(
                id=task.id,
                assignee=None,
                confirmed_by=None,
                name=task.name,
                description=task.description,
                priority=task.priority,
                created_at=task.created_at,
                labels=[
                    LabelDTO(
                        id=label.id,
                        name=label.name,
                        color=label.color
                    )
                    for label in task.labels
                ]
            ) for task in db_tasks
        ]

        await cache.set(
            cache_keys.tasks_not_assigned.format(board_id),
            json.dumps([task.model_dump() for task in tasks], default=str)
        )

        return tasks

    @get('/{board_id:str}/role', responses={
        401: litestar_response_spec(examples=[
            Example('AccessTokenInvalid', value=error.AccessTokenInvalid()),
            Example('AccessTokenExpired', value=error.AccessTokenExpired()),
            Example('AuthorizationHeaderMissing', value=error.AuthorizationHeaderMissing())  # noqa
        ]),
        403: litestar_response_spec(examples=[
            Example('UserNotInBoard', value=error.UserNotInBoard())
        ]),
        422: litestar_response_spec(examples=[
            Example('BoardNotExists', value=error.BoardNotExists())
        ])
    }, tags=[tags.board_handler])
    async def get_role(
        self, auth_client: AccessTokenPayload, db: DataBase, cache: Cache,
        cache_keys: CacheKeys, board_id: str
    ) -> UserRole:
        try:
            valid_board_id = str_to_id(board_id)
        except ValueError as e:
            raise litestar_raise(error.BoardNotExists) from e

        user_role_from_cache = await cache.get(
            cache_keys.user_role_in_board.format(str(auth_client.sub) + board_id)
        )
        if user_role_from_cache:
            return UserRole(int(user_role_from_cache))
        try:
            user_role = await db.get_user_role(
                user_id=auth_client.sub,
                board_id=valid_board_id
            )
        except UserNotFoundError as e:
            raise litestar_raise(error.UserNotInBoard) from e

        await cache.set(
            cache_keys.user_role_in_board.format(str(auth_client.sub) + board_id),
            str(user_role)
        )

        return user_role

    @get('/{task_id:str}/role-by-task', responses={
        401: litestar_response_spec(examples=[
            Example('AccessTokenInvalid', value=error.AccessTokenInvalid()),
            Example('AccessTokenExpired', value=error.AccessTokenExpired()),
            Example('AuthorizationHeaderMissing', value=error.AuthorizationHeaderMissing())  # noqa
        ]),
        403: litestar_response_spec(examples=[
            Example('UserNotInBoard', value=error.UserNotInBoard())
        ]),
        422: litestar_response_spec(examples=[
            Example('BoardNotExists', value=error.BoardNotExists())
        ])
    }, tags=[tags.board_handler])
    async def get_role_by_task(
        self, auth_client: AccessTokenPayload, db: DataBase, cache: Cache,
        cache_keys: CacheKeys, task_id: str
    ) -> UserRole:
        try:
            valid_task_id = str_to_id(task_id)
        except ValueError as e:
            raise litestar_raise(error.BoardNotExists) from e

        user_role_from_cache = await cache.get(
            cache_keys.user_role_in_board_by_task.format(
                str(auth_client.sub) + task_id
            )
        )
        if user_role_from_cache:
            return UserRole(int(user_role_from_cache))

        try:
            board_id = await db.get_board_id_by_task(valid_task_id)
        except TaskNotExists as e:
            raise litestar_raise(error.TaskNotExists) from e

        try:
            user_role = await db.get_user_role(
                user_id=auth_client.sub,
                board_id=board_id
            )
        except UserNotFoundError as e:
            raise litestar_raise(error.UserNotInBoard) from e

        await cache.set(
            cache_keys.user_role_in_board_by_task.format(
                str(auth_client.sub) + task_id
            ),
            str(user_role)
        )

        return user_role
