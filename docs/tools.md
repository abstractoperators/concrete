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
```## Additional Classes and Functions Documentation

### Tools Registry
- **`TOOLS_REGISTRY`**: A global dictionary that holds references to all tool classes defined in this module. This allows for dynamic invocation of tool methods via the `invoke_tool` function.

### Error Handling
The module includes robust error handling in the `invoke_tool` function, ensuring that appropriate exceptions are raised when tools or methods are not found, or when parameters are incorrect. This design promotes reliability and ease of debugging.

### Usage Example
To utilize the tools provided in this module, one can invoke methods dynamically using the `invoke_tool` function. For example:
```python
result = invoke_tool('AwsTool', 'build_and_deploy_to_aws', ['my_project_directory'])
```
This line would call the `build_and_deploy_to_aws` method of the `AwsTool` class, passing in the specified project directory name as an argument.

### Future Enhancements
- **Improved Error Handling**: Consider implementing more granular error handling to provide clearer feedback on specific failures.
- **Logging**: Integrate a logging framework to capture detailed logs of operations, which can aid in troubleshooting and monitoring.
- **Testing**: Develop a comprehensive suite of unit tests to ensure the reliability of each tool and its methods.

### Conclusion
This module serves as a powerful toolkit for developers looking to integrate various services and functionalities into their applications. By following the established patterns and structures, developers can easily extend the module with new tools and capabilities.