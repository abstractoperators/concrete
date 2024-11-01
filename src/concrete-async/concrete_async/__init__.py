from collections.abc import Callable

import concrete_core
from celery.result import AsyncResult

from .models import KombuMixin, Operation
from .tasks import abstract_operation


def _delay_factory(string_func: Callable[..., str]) -> Callable[..., AsyncResult]:
    def _delay(
        self: concrete_core.abstract.AbstractOperator,
        *args,
        options: dict,
        **kwargs,
    ) -> AsyncResult:
        arg_dict = {
            "messages": [
                {"role": "system", "content": options["instructions"]},
                {"role": "user", "content": string_func(self, *args, **kwargs)},
            ],
            "message_format": concrete_core.clients.OpenAIClient.model_to_schema(options["response_format"]),
        }
        operation = Operation(
            client_name=self.llm_client,
            function_name=self.llm_client_function,
            arg_dict=arg_dict,
        )

        clients = {}
        for name, client in self.clients.items():
            client_model = concrete_core.models.clients.OpenAIClientModel(
                model=client.model,
                temperature=client.default_temperature,
            )

            clients[name] = client_model

        operation_result = abstract_operation.delay(operation=operation, clients=clients)
        return operation_result

    return _delay


for operator_name, operator in concrete_core.abstract.AbstractOperatorMetaclass.OperatorRegistry.items():
    for attr, method in operator.__dict__.items():
        if attr.startswith("__") or attr in {"_qna", "qna"} or not callable(method):
            continue
        setattr(method, "_delay", _delay_factory(method))


for message_name, message in concrete_core.models.messages.MESSAGE_REGISTRY.items():
    new_class = type(
        message.__name__,
        (KombuMixin, message),
        {'__module__': message.__module__},
    )
    setattr(concrete_core.models.messages, message.__name__, new_class)
    concrete_core.models.messages.MESSAGE_REGISTRY[message_name] = new_class

original_model = concrete_core.models.clients.OpenAIClientModel

setattr(
    concrete_core.models.clients,
    original_model.__name__,
    type(
        original_model.__name__,
        (KombuMixin, original_model),
        {'__module__': original_model.__module__},
    ),
)
