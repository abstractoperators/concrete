# Hello World

Let's go ahead and make our "Hello World" equivalent for `concrete`.
The goal by the end of this exercise is to not only have a literal "Hello World" application, but also understand how and why we got there.

You *could* achieve the same output by running 

```shell
poetry run python -m concrete prompt "Create a simple hello world program"
```

or simply our Makefile-defined shorthand we've provided for your convenience:
```shell
make helloworld
```

but then you wouldn't necessarily be learning anything.
What we'll be making is in fact a simpler version of what's in `concrete.main`, so feel free to take a look at that to get a better understanding of what's going on.

## Create an Orchestrator

```python hl_lines="1 4"
from concrete.orchestrator import SoftwareOrchestrator


so = SoftwareOrchestrator()
```

An **Orchestrator** is the highest-order grouping of concepts we have in `concrete`.
It encapsulates a set of projects, operators, tools, and clients used for a common purpose, e.g. a virtual engineering department.
A **Software Orchestrator** is just an Orchestrator specifically designed for software development.
It comes pre-equipped with two operators: one executive, and one developer.

## Create a Project

```python hl_lines="5-7"
from concrete.orchestrator import SoftwareOrchestrator


so = SoftwareOrchestrator()
project_output = so.process_new_project(
    "Create a simple hello world program",
)
```

A **Project** is a well-defined, structured hierarchy of operators.
On the surface, you can interact with it much the same as with ChatGPT or any single-agent LLM; simply define it with the desired prompt.
Under the hood, however, the agents participating in the Project work together to complete the prompt, conversing with one another to verify each other's knowledge and validate the proposed solution(s).
A **Software Project** asks the executive to create a plan from the given prompt; the executive feeds this plan step by step to the developer, which generates code to meet the requirements detailed in the current step.

## Run the Project

```python hl_lines="9-11"
from concrete.orchestrator import SoftwareOrchestrator


so = SoftwareOrchestrator()
project_output = so.process_new_project(
    "Create a simple hello world program",
)

for operator, result in [_ async for _ in project_output]:
    print(f"{operator}:")
    print(result)
```

`process_new_project` returns an `AsyncGenerator` that yields tuples of form `(operator_name, operator_output)`.
The results will be in chronological order; that is, printing out the results like we have here lets you see the whole conversation between our executive and developer!
Go ahead and try running the same code with different prompts; instead of `"Create a simple hello world program"`, consider "Create a basic calculator application".