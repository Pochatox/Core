# flake8-in-file-ignores: noqa: WPS110, WPS400

from litestar.handlers import get, post
from litestar.openapi.spec import Example

from app import errors as error
from app import openapi_tags as tags
from app.config import BoardConfig, DataBase
from app.db.abc.base import str_to_id
from app.db.exc import ColumnNotExists, UserNotFoundError
from app.errors import litestar_raise, litestar_response_spec
from app.handlers.controller import BaseController
from app.handlers.dto import (BoardDTO, ColumnDTO, ColumnPreviewDTO,
                              ColumnShortDTO,
                              CreateBoardDTO, CreateColumnDTO,
                              CreateLabelDTO,
                              LabelDTO, LabelShortDTO,
                              ShortTaskDTO, TaskTransitionDTO,
                              UserPreviewDTO, UserShortDTO, TaskPreviewDTO)
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
        user = await db.get_user(board.owner_id)
        return BoardDTO(
            id=board.id,
            owner=UserShortDTO(
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
        self, auth_client: AccessTokenPayload, db: DataBase, board_id: str
    ) -> BoardDTO:
        try:
            board_valid_id = str_to_id(board_id)
        except ValueError as e:
            raise litestar_raise(error.BoardNotExists) from e
        if not await db.is_user_in_board(auth_client.sub, board_valid_id):
            raise litestar_raise(error.UserNotInBoard)
        board = await db.get_board(board_valid_id)
        return BoardDTO(
            id=board.id,
            owner=UserShortDTO(
                username=board.owner.username,
                first_name=board.owner.first_name,
                last_name=board.owner.last_name,
                avatar=board.owner.avatar
            ),
            name=board.name,
            description=board.description,
            created_at=board.created_at,
            columns=[
                ColumnShortDTO(
                    name=column.name,
                    position=column.position,
                    wip=column.wip,
                    tasks=[
                        ShortTaskDTO(
                            assignee=UserPreviewDTO(
                                username=task.assignee.username,
                                avatar=task.assignee.avatar
                            ) if task.assignee else None,
                            confirmed_by=UserPreviewDTO(
                                username=task.confirmed_by.username,
                                avatar=task.confirmed_by.avatar
                            ) if task.confirmed_by else None,
                            name=task.name,
                            description=task.description,
                            priority=task.priority,
                            created_at=task.created_at,
                            labels=[
                                LabelShortDTO(name=label.name, color=label.color)
                                for label in task.labels
                            ]
                        )
                        for task in column.tasks
                    ]
                )
                for column in board.columns
            ],
            labels=[
                LabelDTO(
                    id=label.id,
                    name=label.name,
                    color=label.color
                ) for label in board.labels
            ]
        )

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
        self, auth_client: AccessTokenPayload, db: DataBase, data: CreateColumnDTO
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
        self, auth_client: AccessTokenPayload, db: DataBase, column_id: str
    ) -> ColumnDTO:
        try:
            valid_column_id = str_to_id(column_id)
        except ValueError as e:
            raise litestar_raise(error.ColumnNotExists) from e
        if not await db.is_user_in_board_by_column(auth_client.sub, valid_column_id):
            raise litestar_raise(error.UserNotInBoard)

        try:
            column = await db.get_column(valid_column_id)
        except ColumnNotExists as e:
            raise litestar_raise(error.ColumnNotExists) from e

        return ColumnDTO(
            id=column.id,
            board_id=column.board_id,
            name=column.name,
            description=column.description,
            position=column.position,
            wip=column.wip,
            created_at=column.created_at,
            tasks=[
                ShortTaskDTO(
                    assignee=UserPreviewDTO(
                        username=task.assignee.username,
                        avatar=task.assignee.avatar
                    ) if task.assignee else None,
                    confirmed_by=UserPreviewDTO(
                        username=task.confirmed_by.username,
                        avatar=task.confirmed_by.avatar
                    ) if task.confirmed_by else None,
                    name=task.name,
                    description=task.description,
                    priority=task.priority,
                    created_at=task.created_at,
                    labels=[
                        LabelShortDTO(name=label.name, color=label.color)
                        for label in task.labels
                    ]
                )
                for task in column.tasks
            ]
        )

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
        self, auth_client: AccessTokenPayload, db: DataBase, data: CreateLabelDTO
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
        self, auth_client: AccessTokenPayload, db: DataBase, board_id: str
    ) -> list[ShortTaskDTO]:
        try:
            valid_board_id = str_to_id(board_id)
        except ValueError as e:
            raise litestar_raise(error.BoardNotExists) from e
        if not await db.is_user_in_board(auth_client.sub, valid_board_id):
            raise litestar_raise(error.UserNotInBoard)
        tasks = await db.get_confirmed_tasks(valid_board_id)
        return [
            ShortTaskDTO(
                assignee=UserPreviewDTO(
                    username=task.assignee.username,
                    avatar=task.assignee.avatar
                ) if task.assignee else None,
                confirmed_by=UserPreviewDTO(
                    username=task.confirmed_by.username,
                    avatar=task.confirmed_by.avatar
                ) if task.confirmed_by else None,
                name=task.name,
                description=task.description,
                priority=task.priority,
                created_at=task.created_at,
                labels=[
                    LabelShortDTO(name=label.name, color=label.color)
                    for label in task.labels
                ]
            ) for task in tasks
        ]

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
        self, auth_client: AccessTokenPayload, db: DataBase, board_id: str
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
        if user_role < self.config.min_create_column_role:
            raise litestar_raise(error.InsufficientRoleError)

        task_transitions = await db.get_task_transitions(valid_board_id)
        return [
            TaskTransitionDTO(
                task=TaskPreviewDTO(
                    assignee=UserPreviewDTO(
                        username=tt.task.assignee.username,
                        avatar=tt.task.assignee.avatar,
                    ) if tt.task.assignee else None,
                    confirmed_by=UserPreviewDTO(
                        username=tt.task.confirmed_by.username,
                        avatar=tt.task.confirmed_by.avatar,
                    ) if tt.task.confirmed_by else None,
                    name=tt.task.name,
                    priority=tt.task.priority,
                    created_at=tt.task.created_at,
                ),
                user=UserPreviewDTO(
                    username=tt.user.username,
                    avatar=tt.user.avatar,
                ),
                column=ColumnPreviewDTO(
                    name=tt.column.name,
                    position=tt.column.position,
                ),
                moved_at=tt.moved_at,
            )
            for tt in task_transitions
        ]
