from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import timedelta
from typing import Callable, Generic, Self, TypeVar

from kapusta import Kapusta, Task, KapustaError

from app.task_managers.configs import BaseTaskManagerConfig, KapustaConfig
from app.types import UserId


class TaskManagerError(Exception): ...


TaskManagerConfig = TypeVar('TaskManagerConfig', bound=BaseTaskManagerConfig)


@dataclass
class Tasks:
    del_inactive_user: Callable


@dataclass
class BaseAsyncTaskManager(ABC, Generic[TaskManagerConfig]):
    config: TaskManagerConfig
    tasks: Tasks

    @abstractmethod
    async def connect(self) -> Self: ...

    @abstractmethod
    async def del_inactive_user(
        self, user_id: UserId, eta_delta: timedelta
    ) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...

    def get_tasks_list(self) -> list[Callable]:
        return [
            self.tasks.del_inactive_user
        ]


@dataclass
class KapustaTaskManager(BaseAsyncTaskManager[KapustaConfig]):

    async def connect(self) -> Self:
        self.kapusta = Kapusta(
            crud=self.config.crud,
            logger=self.config.logger,
            max_tick_interval=self.config.max_tick_interval,
            default_overdue_time_delta=self.config.default_overdue_time_delta,
            default_max_retry_attempts=self.config.default_max_retry_attempts,
            default_timeout=self.config.default_timeout
        )
        await self.kapusta.startup()

        self.kapusta_tasks: dict[Callable, Task] = {}
        for task in self.get_tasks_list():
            self.kapusta_tasks[task] = self.kapusta.register_task(task)

        return self

    async def del_inactive_user(
        self, user_id: UserId, eta_delta: timedelta
    ) -> None:
        try:
            update_params = {'eta_delta': eta_delta} if eta_delta else {}
            await self.kapusta_tasks[self.tasks.del_inactive_user].launch(
                update_params=update_params,
                user_id=user_id
            )
        except KapustaError as e:
            raise TaskManagerError from e

    async def close(self) -> None:
        await self.kapusta.shutdown()
