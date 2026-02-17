# flake8-in-file-ignores: noqa: WPS110, WPS400

from uuid import UUID
from litestar.handlers import get, post
from litestar.openapi.spec import Example

from app import errors as error
from app import openapi_tags as tags
from app.config import BoardConfig, DataBase
from app.errors import litestar_raise, litestar_response_spec
from app.handlers.controller import BaseController
from app.handlers.dto import (BoardDTO, ColumnShortDTO, CreateBoardDTO,
                              LabelShortDTO, ShortTaskDTO, UserPreviewDTO,
                              UserShortDTO)
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
        ])
    }, tags=[tags.board_handler])
    async def board(
        self, auth_client: AccessTokenPayload, db: DataBase, board_id: str
    ) -> BoardDTO:
        try:
            board_uuid = UUID(board_id)
        except ValueError as e:
            raise litestar_raise(error.BoardNotExists) from e
        if not await db.is_user_in_board(auth_client.sub, board_id):
            raise litestar_raise(error.UserNotInBoard)
        board = await db.get_board(board_uuid)
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
