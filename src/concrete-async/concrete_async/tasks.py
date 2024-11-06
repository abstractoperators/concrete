from typing import Any, Callable, cast

import concrete

from .celery import app
from .models import ConcreteChatCompletion, KombuMixin, Operation


@app.task(name='concrete_async.tasks.abstract_operation')
def abstract_operation(operation: Operation, clients: dict[str, KombuMixin]) -> Any:
    """
    An operation that's able to execute arbitrary methods on operators/agents
    """
    client = concrete.clients.OpenAIClient(**clients[operation.client_name].model_dump())
    func: Callable[..., Any] = getattr(client, operation.function_name)

    res = func(**operation.arg_dict).model_dump()
    message_format_name = cast(dict, operation.arg_dict["message_format"])["json_schema"]["name"]
    res["message_format_name"] = message_format_name

    return ConcreteChatCompletion(**res).message
