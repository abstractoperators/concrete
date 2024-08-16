from ..celery import app
from .bases import OpenAiOperation


class ExecutiveOperation(OpenAiOperation):
    """
    Represents an Operator that instructs and guides other Operators.
    """

    def __init__(self):
        super().__init__()
        self.instructions = (
            "You are an expert executive software developer."
            "You will follow the instructions given to you to complete each task."
        )


@app.task(base=ExecutiveOperation)
def plan_components(starting_prompt) -> str:
    return """\
    List the essential code components required to implement the project idea. Each component should be atomic,\
    such that a developer could implement it in isolation provided placeholders for preceding components.

    Your responses must:
    1. Include specific components
    2. Be comprehensive, accurate, and complete
    3. Use technical terms appropriate for the specific programming language and framework
    4. Sequence components logically, with later components dependent on previous ones
    5. Not include implementation details or code snippets
    6. Assume all dependencies are already installed but NOT imported
    7. Be decisive and clear, avoiding ambiguity or vagueness
    8. Be declarative, using action verbs to describe the component.
    ...

    Project Idea:
    {starting_prompt}
    """.format(
        starting_prompt=starting_prompt
    )


@app.task(base=ExecutiveOperation)
def answer_question(context: str, question: str) -> str:
    """
    Prompts the Operator to answer a question
    Returns the answer
    """
    return (
        f"Context: {context} Developer's Question: {question}\n "
        "As the senior advisor, answer with specificity the developer's question about this component. "
        "If there is no question, then respond with 'Okay'. Do not provide clarification unprompted."
    )


@app.task(base=ExecutiveOperation)
def generate_summary(summary: str, implementation: str) -> str:
    """
    Generates a summary of completed components
    Returns the summary
    """
    prompt = """Summarize what has been implemented in the current component,
    and append it to the previously summarized components.

    For each component summary:
    1. Describe its full functionality using natural language.
    2. Include file name, function name, and variable name in the description.

    Example Output:
    1. Imported the packages numpy as np, and pandas as pd in app.py
    2. Instantiated a pandas dataframe named foo, with column names bar and baz in app.py
    3. Populated foo with random ints in app.py
    4. Printed average of bar and baz in the main function of app.py

    Previous Components: {summary}
    Current Component Implementation: {implementation}
    """.format(
        summary=summary, implementation=implementation
    )
    return prompt
