from abc import ABC, abstractmethod
from typing import Any, Protocol


class EmailEngine(ABC):
    @abstractmethod
    async def send_email(
        self, to_email: str | list[str], subject: str, body: dict, template_name: str
    ) -> None:
        pass


class Notifier(Protocol):
    def notify(self, *args: Any, **kwargs: Any) -> None: ...
