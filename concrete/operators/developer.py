from textwrap import dedent

from ..celery import app
from .bases import OpenAiOperation


class DeveloperOperation(OpenAiOperation):
    def __init__(self):
        super().__init__()
        self.instructions = (
            "You are an expert software developer. You will follow the instructions given to you to complete each task."
            "You will follow example formatting, defaulting to no formatting if no example is provided."
        )


@app.task(base=DeveloperOperation)
def ask_question(context: str) -> str:
    """
    Accept instructions and ask a question about it if necessary.

    Can return `no question`.
    """
    return dedent(
        f"""
        *Context:*
        {context}

        If necessary, ask one essential question for continued implementation.
        If no question is necessary, respond 'No Question'.

        **Example:**
            Context:
            1. Imported the Flask module from the flask package
            Current Component: Create a Flask application instance
            Clarification: None

            No Question


        **Example:**
            Context:
            1. The code imported the Flask module from the flask package
            2. The code created a Flask application named "app"
            3. Created a route for the root URL ('/')
            Current Component: Create a function that will be called when the root URL is accessed.\
            This function should return HTML with a temporary Title, Author, and Body Paragraph

            What should the function be called?"""
    )


@app.task(base=DeveloperOperation)
def implement_component(context: str) -> str:
    """
    Prompts the Operator to implement a component based off of the components context
    Returns the code for the component
    """
    return """
        Please provide complete and accurate code for the provided current component.\
        Produced code blocks should be preceded by the file where it should be placed.
        Use placeholders referencing code/functions already provided in the context. Never provide unspecified code.

        **Example:**
            Context:
            1. Imported the Flask module from the flask package
            Current Component: Create a flask application instance named 'app'
            Clarification: None

            Output:
            app.py
            ```python
            app = Flask(app)
            ```

        **Example:**
            Context:
            1. The code imported the Flask module from the flask package
            2. The code created a Flask application named "app"
            3. Created a route for the root URL ('/')
            Current Component: Create a function that will be called when the root URL is accessed.
            Question: What should the function do?
            Clarification: The function should do nothing. It should be a placeholder for future functionality.

            Output:
            app.py
            ```python
            def index():
                pass
            ```

        **Example:**
            Context:
                1. The code imported the Flask module from the flask package
                2. The code created a Flask application named "app"
                3. Created a route for the root URL ('/')
                4. Created a placeholder function named 'index' that does nothing
                Current Component: Create an html file that will be rendered when the root URL is accessed

                Output:
                templates/index.html
                ```html
                <!DOCTYPE html>
                ```html
                
        *Context:*
        {context}
    """.format(
        context=context
    )


@app.task(base=DeveloperOperation)
def integrate_components(
    planned_components: list[str],
    implementations: list[str],
    webpage_idea: str,
) -> str:
    """
    Prompts Operator to combine code implementations of multiple components
    Returns the combined code
    """
    prev_components = []
    for desc, code in zip(planned_components, implementations):
        prev_components.append(f"\n\t****Component description****: \n{desc}\n\t****Code:**** \n{code}")

    out_str = """\
        *Task: Accurately and completely implement the original webpage creation task using the provided components*
        **Webpage Idea:**
            {webpage_idea}

        **Components:**
            {components}
            
        **Important Details:**
        1. All necessary imports and libraries are at the top of each file
        2. Each code block is preceded by a file path where it should be placed
        3. Code is organized logically
        4. Resolve duplicate and conflicting code with discretion
        5. Only code and file paths are returned
        6. With discretion, modify existing implementations to ensure a working implementation of the\
        original webpage creation task.

        **Example Output Syntax:**
        app.py
        ```python
        def foo():
            pass
        ```

        templates/home.html
        ```html
        <!DOCTYPE html>
        ```
        """.format(
        webpage_idea=webpage_idea, components="".join(prev_components)
    )
    return out_str


@app.task(base=DeveloperOperation)
def implement_html_element(prompt: str) -> str:
    out_str = f"""\
    Generate an html element with the following description:\n
    {prompt}

    Generated html elements should be returned as a string with the following format.
    Remember to ONLY return the generated HTML element. Do not include any other information.

    Example 1.
    Generate an html element with the following description:
    A header that says `Title`
    
    <h1>Title</h1>

    Example 2.
    Generate an html element with the following description:
    An input form with a submit button
    
    <form method="POST" action="/">
    <label for="textInput">Input:</label>
    <input type="text" id="textInput" name="textInput" required>
    <button type="submit">Submit</button>
    </form>
    
    Example 3.
    Generate an html element with the following description:
    Create a paragraph with the text `Hello, World!`
    
    <p>Hello, World!</p>
    """
    return out_str
