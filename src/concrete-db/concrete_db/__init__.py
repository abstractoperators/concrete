from collections.abc import Callable
from functools import wraps

from concrete.abstract import AbstractOperator
from concrete.clients import CLIClient
from concrete.models.messages import Message

from .crud import create_message
from .orm import Session
from .orm.models import MessageCreate


def _qnawrapper(_qna: Callable) -> Callable:
    @wraps(_qna)
    def decorator(
        self: AbstractOperator,
        query: str,
        response_format: type[Message],
        instructions: str | None = None,
    ) -> Message:
        answer = _qna(self, query, response_format, instructions)
        if self.store_messages:
            with Session() as session:
                create_message(
                    session,
                    MessageCreate(
                        type=response_format.__name__,
                        content=repr(answer),
                        prompt=self.starting_prompt,
                        project_id=self.project_id,
                        operator_id=self.operator_id,
                    ),
                )
        return answer

    return decorator


AbstractOperator._qna = _qnawrapper(AbstractOperator._qna)  # type: ignore[assignment]

CLIClient.emit("concrete-db initialized")
