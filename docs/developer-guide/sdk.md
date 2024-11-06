# Operators

## Abstract Operators

Abstract Operators are the base building block of Operators. They handle a lot of magic behind the scenes, enabling asynchronous LM calls, saving of messages, and tool invocations.

### `__init__`
    
- clients (dict[str, LMClient]): A dictionary of LM clients available to the operator. The key is the enumerated name of the client (e.g. `'openai'`), and the value is the client wrapper object `LMClient`.

- tools (list[MetaTool]): A list of of Tools available to the operator. These tools are made available when `options['use_tools'] = True`. Similarly, `options['tools'] = [tool1, ...]` overrides the default list of tools. 

- operator_id (uuid): A unique identifier for the operator. This is used to save messages and other data. 

- project_id (uuid): A unique identifier for the project. This is used to save messages and other data.

- starting_prompt (str): The starting project prompt.

- store_messages (bool): Whether to store messages in the databases. Only works when the package `concrete-db` is installed.

- response_format (type[Message]): The response format of the operator. Message is a wrapper class for Pydantic Models which are used for OpenAI Structured Outputs.

- run_async (bool): Whether to run qna calls asynchronously via Celery. Only works when the package `concrete-celery` is installed and imported in the application. Also requires that a `celery` application is started. 

### `_qna`

foo
## Operators

Operators are defined by instructions and string returning functions.

```
from concrete-core.operators import Operator

operator = Operator()
```
# Tools

Last Updated: 2024-11-06 15:55:36 UTC

Lines Changed: +37, -0