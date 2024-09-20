## Operators  
Operators are AI agents with predefined system instructions and prompt interactions. They form the core of the Concrete as an Orchestration platform. Operators complete chat-completion based tasks. Syntactically meaningful outputs enable integrations with other modules, like [tools](tools.md)

### How to use your first operator
**Install Concrete**  
First install python and concrete using pip:
```
pip install concrete
```

**Create an operator**
```python
from concrete import operators

operator = operators.Operator()
operator.chat("Hey there, operator!")
```

### How to create a custom operator

It's easy to create a custom operator. First, clone our repository at [concrete](https://github.com/abstractoperators/concrete). Then, 

 Create a new class that inherits from `concrete.operators.Operator`. 