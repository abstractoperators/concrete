# Tools
`Tools` allow an operator to interact with the real world or internet.

Some tools we have supported are:  

- AWSTool
  - Automatically deploy a project to AWS Cloud  
- GithubTool
  - Interact with Github repositories

Use: Tools are used to provide operators methods that can be used to complete a task. Tools are defined as classes with callable class methods. Providing an Operator with Tools forces it to return a message format subclassing from `Tool` whether or not the tool is used.  
A tool message can be invoked using `concrete.tools.invoke_tool(tool: Tool)`. Similarly, an Operator can invoke a tool using `Operator().invoke_tool(tool: Tool)`.

1. String representation of the tool tells operator what tools are available
   1. Currently implemented with a metaclass defining __str__ for a class (a metaclass instance). The benefit of this is that the class does not need to be instantiated to get its string representation. Similarly, with staticmethods, the class does not need to be instantiated to use its methods. Additionally, methods are stateless.
      1. The benefit of keeping tools inside a toolclass is to provide the tool organized helper functions.
   1. Possible alternatives involving removal of tool class. [repr](https://stackoverflow.com/questions/20093811/how-do-i-change-the-representation-of-a-python-function). This would remove the complicated metaclass entirely in favor of a decorated function.


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


operator.chat("Use your provided tools to calculate the sum of 945 and 624", options={'tools': [Arithmetic]})
```

## How Tools Work

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
```

Under the hood in `Operator.qna`, the tool is invoked and refed to the operator so it can complete the original chat prompt.
Last Updated: 2024-11-18 18:33:48 UTC
Lines Changed: +79, -0