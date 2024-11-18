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

### `add_edge`

Adds a directed edge between two nodes in the DAG.

- child (DAGNode): The downstream node

- parent (DAGNode): The upstream node

- res_name (str): The name of the kwarg to pass as the result of the parent node's task to the child node's task.

- res_transformation (Callable): Optional transformation function to apply to the result before passing it to the child node's task.

### `add_node`

Adds a node to the DAG.

- node (DAGNode): The node to add

### `execute`

Executes the DAG by executing each node in topological order. Returns an AsyncGenerator of messages, with no guarantee of order besides topological order.

### `is_dag`

Helper function for guaranteeing the Project is a DAGProject.

### DagNode

Object representing a node in a DAG. Manages the Operator and task to be executed from it.

#### `__init__`

- task (str): The method on the Operator to be executed
- operator (Operator): The Operator to execute the task
- default_task_kwargs (dict): Default keyword arguments for the task.
- options (dict): Options dict for the Operator qna call. Overrides Project options. Options can also be set in default_task kwargs as the `'options'` key.

#### `update`

Internal method updating the node's task kwargs and options.

#### `execute`

Internal method executing the node's task with provided default kwargs and kwargs passed in from parent nodes.

#### `__str__`

String representation of the node.


Last Updated: 2024-11-18 18:33:48 UTC
Lines Changed: +78, -0
