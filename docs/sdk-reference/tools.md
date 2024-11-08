# Tools

Tools represent an Operators ability to interact with external services and the world. Tools can be invoked by hand, or automatically by the Operator via their `invoke_tool` method.

## `MetaTool`

`MetaTool` provides a string representation of the tool. It uses type hints and documentation strings to create a human-readable representation of the tool.

metaclass from `MetaTool` to create a tool.

## Examples


```python
from concrete.tools import MetaTool
from concrete.tools import invoke_tool
class Arithmetic(metaclass = MetaTool):
    @classmethod
    def sum(cls, x: int, y: int) -> int:
        """
        Returns the sum of two numbers
        """
        return x + y

print(Arithmetic)
```


Last Updated: 2024-11-07 16:47:45 UTC

Lines Changed: +31, -0