## Operators  
Operators are agents with a specific prompt and a set of pre-defined interactions. They are capable of performing well-defined roles, working with other operators, and using tools.


### How to create your first operator  
**Install Concrete**  
First install python and concrete using pip: `pip install concrete`

**Create an operator**
```python
from concrete import operators

operator = operators.Operator()
operator.chat("Hey there, operator!")
```