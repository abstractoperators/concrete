from collections.abc import Callable
from typing import Any, cast

from celery.result import AsyncResult
from concrete_async.tasks import abstract_operation

import concrete
import concrete.abstract
from concrete.clients import CLIClient, model_to_schema
from concrete.models import KombuMixin, Message, Operation


def _delay_factory(string_func: Callable[..., str]) -> Callable[..., AsyncResult]:
    def _delay(
        self: concrete.abstract.AbstractOperator,
        *args,
        options: dict,
        **kwargs,
    ) -> AsyncResult:
        arg_dict: dict[str, list | dict] = {
            "messages": [
                {"role": "system", "content": options["instructions"]},
                {"role": "user", "content": string_func(self, *args, **kwargs)},
            ],
            "message_format": model_to_schema(options["response_format"]),
        }
        operation = Operation(
            client_name=self.llm_client,
            function_name=self.llm_client_function,
            arg_dict=arg_dict,
        )

        clients = {}
        for name, client in self.clients.items():
            client_model = concrete.models.clients.OpenAIClientModel(
                model=client.model,
                temperature=client.default_temperature,
            )

            clients[name] = client_model

        operation_result = abstract_operation.delay(operation=operation, clients=clients)
        return operation_result

    return _delay


for (
    operator_name,
    operator,
) in concrete.abstract.AbstractOperatorMetaclass.OperatorRegistry.items():
    for attr, method in operator.__dict__.items():
        if attr.startswith("__") or attr in {"_qna", "qna"} or not callable(method):
            continue
        setattr(method, "_delay", _delay_factory(method))


for message_name, message in concrete.models.messages.MESSAGE_REGISTRY.items():
    new_class = type(
        message.__name__,
        (cast(type, KombuMixin), cast(Any, message)),
        {"__module__": message.__module__},
    )
    setattr(concrete.models.messages, message.__name__, new_class)
    concrete.models.messages.MESSAGE_REGISTRY[message_name] = cast(Message, new_class)

original_model = concrete.models.clients.OpenAIClientModel

setattr(
    concrete.models.clients,
    original_model.__name__,
    type(
        original_model.__name__,
        (KombuMixin, original_model),
        {"__module__": original_model.__module__},
    ),
)

CLIClient.emit("concrete-async initialized")
