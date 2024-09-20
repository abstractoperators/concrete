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
class Arithmetic(metaclass=ToolClass):
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