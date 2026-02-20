# flake8-in-file-ignores: noqa: WPS110, WPS400

from litestar.handlers import get, post
from litestar.openapi.spec import Example

from app import errors as error
from app import openapi_tags as tags
from app.config import BoardConfig, DataBase
from app.db.abc.base import str_to_id
from app.db.abc.models import ColumnProtocol, TaskProtocol
from app.db.exc import ColumnNotExists, TaskNotExists, UserNotFoundError
from app.errors import litestar_raise, litestar_response_spec
from app.handlers.controller import BaseController
from app.handlers.dto import (BoardDTO, ColumnDTO, ColumnShortDTO,
                              CreateBoardDTO, CreateColumnDTO, CreateTaskDTO,
                              LabelShortDTO, ShortTaskDTO, TaskDTO,
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
            created_ad=board.created_at,
            columns=[]
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
        if not await db.is_user_in_board(auth_client.sub, board_id):
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
            created_ad=board.created_at,
            columns=[
                ColumnShortDTO(
                    name=column.name,
                    position=column.position,
                    wip=column.wip,
                    tasks=[
                        ShortTaskDTO(
                            assigne=UserPreviewDTO(
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
            ]
        )

    @post('/task', responses={
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
    }, tags=[tags.board_handler])
    async def create_task(
        self, auth_client: AccessTokenPayload, db: DataBase, data: CreateTaskDTO
    ) -> TaskDTO:
        try:
            user_role = await db.get_user_role(
                user_id=auth_client.sub,
                board_id=data.board_id
            )
        except UserNotFoundError as e:
            raise litestar_raise(error.UserNotExists) from e
        if user_role < self.config.min_create_task_role:
            raise litestar_raise(error.InsufficientRoleError)

        try:
            task: TaskProtocol = await db.create_task(
                board_id=data.board_id,
                name=data.name,
                description=data.description,
                priority=data.priority,
                user_id=auth_client.sub
            )
        except ColumnNotExists as e:
            raise litestar_raise(error.ColumnNotExists) from e
        return TaskDTO(
            id=task.id,
            board_id=task.board_id,
            column_id=task.column_id,
            assignee_id=task.assignee_id,
            confirmed_by_id=task.confirmed_by_id,
            name=task.name,
            description=task.description,
            priority=task.priority,
            created_at=task.created_at
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
            column: ColumnProtocol = await db.create_column(
                board_id=data.board_id,
                name=data.name,
                description=data.description,
                wip=data.wip
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
            column = await db.get_column(column_id)
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
                    assigne=UserPreviewDTO(
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

    @get('/task/{task_id:str}', responses={
        401: litestar_response_spec(examples=[
            Example('AccessTokenInvalid', value=error.AccessTokenInvalid()),
            Example('AccessTokenExpired', value=error.AccessTokenExpired()),
            Example('AuthorizationHeaderMissing', value=error.AuthorizationHeaderMissing())  # noqa
        ]),
        422: litestar_response_spec(examples=[
            Example('ColumnNotExists', value=error.InvalidColumnPosition())
        ])
    }, tags=[tags.board_handler])
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
            task = await db.get_task(task_id)
        except TaskNotExists as e:
            raise litestar_raise(error.TaskNotExists) from e

        return TaskDTO(
            id=task.id,
            board_id=task.board_id,
            column_id=task.column_id,
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
            created_at=task.created_at
        )
