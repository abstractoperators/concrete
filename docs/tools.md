## Tools
`Tools` allow an operator to interact with the real world or internet.

Some tools we have supported are:  
- AWSTool
  - Automatically deploy a project to AWS Cloud  
- GithubTool
  - Interact with Github repositories
- KnowledgeGraphTool
  - Converts a directory into a Knowledge Graph

Use: Tools are used to provide operators methods that can be used to complete a task. Tools are defined as classes with methods that can be called. Operators are expected to return a list of called tools with syntax [Tool1, Tool2, ...]
A returned tool syntax is expected to be evaluated using `tools.invoke_tool`

1. String representation of the tool tells operator what tools are available
   1. Currently implemented with a metaclass defining __str__ for a class (a metaclass instance). The benefit of this is that the class does not need to be instantiated to get its string representation. Similarly, with staticmethods, the class does not need to be instantiated to use its methods
      1. The benefit of keeping tools inside a toolclass is to provide the tool organized helper functions.
   2. Possible alternatives involving removal of tool class. [repr](https://stackoverflow.com/questions/20093811/how-do-i-change-the-representation-of-a-python-function). This would remove the complicated metaclass entirely in favor of a decorated function.

2) TODO: Update prompting to get good tool call behavior.

Example:
In this example, TestTool is an example Tool that can be provided to an operator qna.
Tools should have syntax documented in their docstrings so the operator knows how to use them.

```python
from concrete.tools import MetaTool
class Arithmetic(metaclass=MetaTool):
    @classmethod
    def add(cls, x: int, y: int) -> int:
        '''
        x (int): The first number
        y (int): The second number

        Returns the sum of x and y
        '''
        return x + y
    
    @classmethod
    def subtract(cls, x: int, y: int) -> int:
        '''
        x (int): The first number
        y (int): The second number

        Returns the difference of x and y
        '''
        return x - y
    
    # ...


tool_call = operators.Operator().chat("Use your provided tools to calculate the sum of 945 and 624", [Arithmetic], message_format=Tool)
res = invoke_tool(**tool_call.model_dump())
```

### How Tools Work
When you pass Tools to an Operator, AO converts the tool into a string representation. This string representation is given to the Operator in its chat completion prompt. The Operator uses its discretion to decide which (if any) tool to use, and returns a syntactically correct Tool call.

An example trace of `Arithmetic.__str__` looks something like
```python
print(Arithmetic)
'''
Arithmetic Tool with methods:
   - add(cls, x: int, y: int) -> int
        x (int): The first number
        y (int): The second number

        Returns the sum of x and y
   - subtract(cls, x: int, y: int) -> int
        x (int): The first number
        y (int): The second number

        Returns the difference of x and y
'''
```## Tools Module Documentation

### Overview
The `Tools` module provides a set of classes that allow operators to interact with various external systems and services. Each tool is designed to encapsulate specific functionalities, making it easier for operators to perform tasks without needing to understand the underlying implementation details.

### Tool Classes

#### MetaTool
- **Purpose**: A metaclass that dynamically generates string representations for tool classes, allowing operators to see available methods without instantiating the class.
- **Key Features**:
  - Automatically constructs a string representation of the class methods and their signatures.
  - Registers the tool class in the `TOOLS_REGISTRY` for easy access.

#### HTTPTool
- **Purpose**: Facilitates making HTTP requests to specified URLs.
- **Methods**:
  - `request(method: str, url: str, **kwargs) -> Union[dict, str, bytes]`: Makes an HTTP request and processes the response.
  - `get(url: str, **kwargs) -> Response`: Sends a GET request.
  - `post(url: str, **kwargs) -> Response`: Sends a POST request.
  - `put(url: str, **kwargs) -> Response`: Sends a PUT request.
  - `delete(url: str, **kwargs) -> Response`: Sends a DELETE request.

#### RestApiTool
- **Purpose**: Extends `HTTPTool` to specifically handle RESTful API interactions, particularly with JSON responses.
- **Methods**:
  - Inherits all methods from `HTTPTool` and overrides `_process_response` to handle JSON content.

#### AwsTool
- **Purpose**: Provides functionalities to build and deploy applications to AWS.
- **Methods**:
  - `build_and_deploy_to_aws(project_directory_name: str) -> None`: Builds a Docker image and deploys it to AWS.
  - `_build_and_push_image(project_directory_name: str) -> tuple[bool, str]`: Builds and pushes the Docker image to ECR.
  - `_deploy_service(containers: list[Container], ...)`: Deploys a service to AWS ECS.

#### GithubTool
- **Purpose**: Facilitates interactions with GitHub repositories through its RESTful API.
- **Methods**:
  - `make_pr(owner: str, repo: str, branch: str, title: str = "PR", base: str = "main") -> dict`: Creates a pull request.
  - `make_branch(org: str, repo: str, base_branch: str, new_branch: str, access_token: str)`: Creates a new branch from a specified base branch.
  - `delete_branch(org: str, repo: str, branch: str, access_token: str)`: Deletes a specified branch.
  - `put_file(org: str, repo: str, branch: str, commit_message: str, path: str, file_contents: str, access_token: str)`: Updates or creates a file in the repository.
  - `get_diff(org: str, repo: str, base: str, compare: str, access_token: str)`: Retrieves the diff between two branches.

#### KnowledgeGraphTool
- **Purpose**: Converts a directory structure into a knowledge graph representation.
- **Methods**:
  - `parse_to_tree(org: str, repo: str, dir_path: str, rel_gitignore_path: str | None = None) -> UUID`: Parses a directory into a knowledge graph.
  - `_chunk(parent_id: UUID, ignore_paths) -> list[UUID]`: Chunks a node into smaller nodes for processing.
  - `_summarize(node_id: UUID) -> str`: Summarizes a node based on its type (file or directory).

### Usage
Operators can utilize these tools by invoking their methods as needed. Each tool class provides a clear interface for performing specific tasks, and operators are expected to return a list of called tools using the syntax `[Tool1, Tool2, ...]`. The returned tool syntax should be evaluated using `tools.invoke_tool`.

### Example
```python
from concrete.tools import MetaTool
class Arithmetic(metaclass=MetaTool):
    @classmethod
    def add(cls, x: int, y: int) -> int:
        '''
        x (int): The first number
        y (int): The second number

        Returns the sum of x and y
        '''
        return x + y

    @classmethod
    def subtract(cls, x: int, y: int) -> int:
        '''
        x (int): The first number
        y (int): The second number

        Returns the difference of x and y
        '''
        return x - y

# Example usage of tools

```