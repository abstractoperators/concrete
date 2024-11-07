# Projects

## Software Project

### `__init__`

- starting_prompt (str): The starting prompt for the project
- orchestrator (Orchestrator): The orchestrator managing this Project's resources.
- exec (Executive): The executive operator for this project
- dev (Developer): The developer operator for this project
- clients: (dict[str, LMClient]): The language model clients for this project, e.g. `{'openai': OpenAIClient()}`

### `do_work`

Breaks down the starting prompt into smaller components and writes the code for each individually. 

Returns an AsyncGenerator

## Dag Project

Represents a Directed Acyclic Graph (DAG) of Operator executions. Manages node executions and dependencies.

### `__init__`

- options (dict): Standard options for Operator qna calls. Overridden by Node options.


### DagNode

Object representing a node in a DAG. Manages the Operator and task to be executed from it.





Last Updated: 2024-11-07 21:07:13 UTC
Lines Changed: +29, -0
