from functools import wraps
from textwrap import dedent
from typing import Callable, List, Optional
from uuid import uuid1

from pydantic import BaseModel

from .clients import Client
from .operator_responses import TextResponse
from .tools import MetaTool


class Operator:
    """
    Represents the base Operator for further implementation
    """

    def __init__(
        self,
        clients: dict[str, Client],
        instructions: Optional[str] = None,
    ):
        self.uuid = uuid1()
        self.clients = clients

        # TODO: Move specific software prompting to its own SoftwareOperator class or mixin
        self.instructions = instructions or (
            "You are a software developer. " "You will answer software development questions as concisely as possible."
        )

    def _qna(
        self,
        query: str,
        response_format: Optional[BaseModel] = None,
    ) -> BaseModel:
        """
        "Question and Answer", given a query, return an answer.
        Basically just a wrapper for OpenAI's chat completion API.

        Synchronous.
        """
        instructions = self.instructions
        messages = [
            {'role': 'system', 'content': instructions},
            {'role': 'user', 'content': query},
        ]

        response = (
            self.clients["openai"]
            .complete(
                messages=messages,
                response_format=response_format if response_format else TextResponse,
            )
            .choices[0]
        ).message

        if response.refusal:
            print(f"Operator refused to answer question: {query}")
            raise Exception("Operator refused to answer question")

        answer = response.parsed
        return answer

    @classmethod
    def qna(cls, question_producer: Callable) -> Callable:
        """
        Decorate something on a child object downstream to get a response from a query

        question_producer is expected to return a request like "Create a website that does xyz"
        """

        @wraps(question_producer)
        def _send_and_await_reply(*args, **kwargs):
            self = args[0]
            response_format = kwargs.pop("response_format", None)
            query = question_producer(*args, **kwargs)
            return self._qna(query, response_format=response_format)

        return _send_and_await_reply


class Developer(Operator):
    """
    Represents an Operator that produces code.
    """

    def __init__(self, clients: dict[str, Client]):
        agent_role = (
            "You are an expert software developer. You will follow the instructions given to you to complete each task."
            "You will follow example formatting, defaulting to no formatting if no example is provided."
        )
        super().__init__(clients, agent_role)

    @Operator.qna
    def ask_question(self, context: str) -> str:
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

    @Operator.qna
    def implement_component(self, context: str) -> str:
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

    @Operator.qna
    def integrate_components(
        self,
        planned_components: List[str],
        implementations: List[str],
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

    @Operator.qna
    def use_tools(self, question, tools: List[MetaTool] = []):

        query = ""
        if tools:
            query += """Here are your available tools:\
                Either call the tool with the specified syntax, or leave its field blank.\n"""
            for tool in tools:
                query += str(tool)

        query += """\n\n{question}""".format(question=question)
        return query

    @Operator.qna
    def implement_html_element(self, prompt: str) -> str:
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


class Executive(Operator):
    """
    Represents an Operator that instructs and guides other Operators.
    """

    def __init__(self, clients: dict[str, Client]):
        agent_role = (
            "You are an expert executive software developer."
            "You will follow the instructions given to you to complete each task."
        )
        super().__init__(clients, agent_role)

    @Operator.qna
    def plan_components(self, starting_prompt) -> str:
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

    @Operator.qna
    def answer_question(self, context: str, question: str) -> str:
        """
        Prompts the Operator to answer a question
        Returns the answer
        """
        return (
            f"Context: {context} Developer's Question: {question}\n "
            "As the senior advisor, answer with specificity the developer's question about this component. "
            "If there is no question, then respond with 'Okay'. Do not provide clarification unprompted."
        )

    @Operator.qna
    def generate_summary(self, summary: str, implementation: str) -> str:
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