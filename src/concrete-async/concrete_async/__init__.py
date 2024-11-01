from collections.abc import Callable
from typing import Any

import concrete_core
from celery.result import AsyncResult
from concrete_core.abstract import AbstractOperator, AbstractOperatorMetaclass
from concrete_core.models.base import ConcreteModel
from concrete_core.models.messages import MESSAGE_REGISTRY
from kombu.utils.json import register_type
from pydantic import BaseModel

from .celery import app
from .models import KombuMixin, Operation
from .tasks import abstract_operation


def _delay_factory(string_func: Callable[..., str]) -> Callable[..., AsyncResult]:
    def _delay(
        self: AbstractOperator,
        *args,
        options: dict,
        **kwargs,
    ) -> AsyncResult:
        arg_dict = {
            "messages": [
                {"role": "system", "content": options["instructions"]},
                {"role": "user", "content": string_func(self, *args, **kwargs)},
            ],
            "message_format": options["response_format"].as_response_format(),
        }
        operation = Operation(client_name=self.llm_client, function_name=self.llm_client_function, arg_dict=arg_dict)

        clients = {}
        for name, client in self.clients.items():
            client_model = concrete_core.models.clients.OpenAIClientModel(
                model=client.model,
                temperature=client.temperature,
            )

            clients[name] = client_model

        operation_result = abstract_operation.delay(operation=operation, clients=clients)
        return operation_result

    return _delay


for operator_name, operator in AbstractOperatorMetaclass.OperatorRegistry.items():
    for attr, method in operator.__dict__.items():
        if attr.startswith("__") or attr in {"_qna", "qna"} or not callable(method):
            continue
        setattr(method, "_delay", _delay_factory(method))


for message_name, message in MESSAGE_REGISTRY.items():
    message = type(message_name, (KombuMixin, message), {})


original_model = concrete_core.models.clients.OpenAIClientModel

concrete_core.models.clients.OpenAIClientModel = type(
    original_model.__name__,
    (KombuMixin, original_model),
    {
        '__module__': original_model.__module__,
    },
)
