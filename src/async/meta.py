class AsyncMetaclass(type):
    """
    This metaclass automatically creates a '_delay' version for each method in the class, allowing these methods to be executed asynchronously using Celery workers.
    """  # noqa E501

    def __new__(cls, clsname, bases, attrs):
        # identify methods and add delay functionality
        def _delay_factory(string_func: Callable[..., str]) -> Callable[..., AsyncResult]:

            def _delay(
                self: "AbstractOperator",
                *args,
                options: OperatorOptions,
                **kwargs,
            ) -> AsyncResult:
                # TODO Make generic to support other delayable methods
                # Pop extra kwargs and set defaults
                operation = Operation(
                    client_name=self.llm_client,
                    function_name=self.llm_client_function,
                    arg_dict={
                        "messages": [
                            {"role": "system", "content": options.instructions},
                            {"role": "user", "content": string_func(self, *args, **kwargs)},
                        ],
                        "message_format": OpenAIClient.model_to_schema(options.response_format),
                    },
                )
                # TODO unhardcode client conversion
                client_models = {
                    name: OpenAIClientModel(
                        model=client.model,
                        temperature=client.default_temperature,
                    )
                    for name, client in (self.clients).items()
                }
                operation_result = abstract_operation.delay(
                    operation=operation, clients=client_models
                )  # (celery.result.AsyncResult) - need to .get()
                return operation_result

            return _delay

        # Inspect attrs of a class at interpretation time and process methods
        for attr in attrs:
            if attr.startswith("__") or attr in {"_qna", "qna"} or not callable(attrs[attr]):
                continue

            attrs[attr]._delay = _delay_factory(attrs[attr])

        return super().__new__(cls, clsname, bases, attrs)


class DatabaseMetaclass(type):
    pass


type(name, bases, attrs, **kwargs)

# maybe in .env or settings.py
middleware = [
    AsyncMetaclass,
    DatabaseMetaclass,
]

## Inside abstract.py
