Last Updated: 2024-11-18 18:33:48 UTC
Lines Changed: +16, -0
# Operators  

Operators are agents with a specific prompt and a set of pre-defined interactions. They are capable of performing well-defined roles, working with other operators, and using tools.


## How to create your first operator  

**Create an operator**
```python
from concrete import operators

operator = operators.Operator()
operator.chat("Hey there, operator!")
```