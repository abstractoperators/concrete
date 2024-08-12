import os
import socket
import time
from functools import wraps
from pathlib import Path
from textwrap import dedent
from typing import Callable, List, Optional, cast
from uuid import UUID, uuid1

from .clients import CLIClient, Client


class Operator:
    """
    Represents the base Operator for further implementation
    """

    auto_dedent = True

    def __init__(self, clients: dict[str, Client]):
        self.uuid = uuid1()
        self.clients = clients

        # TODO: Move specific software prompting to its own SoftwareOperator class or mixin
        self.instructions = (
            "You are a software developer. " "You will answer software development questions as concisely as possible."
        )

    def _qna(
        self,
        query: str,
        instructions: Optional[str] = None,
    ):
        """
        "Question and Answer", given a query, return an answer.

        Synchronous.
        """
        instructions = instructions or self.instructions
        messages = [
            {'role': 'system', 'content': instructions},
            {'role': 'user', 'content': query},
        ]
        response = self.clients["openai"].complete(messages=messages, model="gpt-4o-mini")

        answer = response.choices[0].message.content

        return answer

    @classmethod
    def qna(cls, message_producer: Callable) -> Callable:
        """
        Decorate something on a child object downstream to get a response from a query

        message_producer is expected to return a string/prompt.
        """

        @wraps(message_producer)
        def _send_and_await_reply(*args, **kwargs):
            self = args[0]
            instructions = kwargs.pop("instructions", None)
            content = message_producer(*args, **kwargs)
            content = dedent(content) if self.auto_dedent else content
            return self._qna(content, instructions=instructions)

        return _send_and_await_reply


class Developer(Operator):
    """
    Represents an Operator that produces code.
    """

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
    def implement_component(self, context: str, dedent=True) -> str:
        """
        Prompts the Operator to implement a component based off of the components context
        Returns the code for the component
        """
        return f"""
            Provide code for the current component based on existing component implementations in Context.\
            Produced code blocks should be preceded by the file where it should be placed.
            Use placeholders referencing code/functions already provided in the context. Never provide unspecified code.

            *Context:*
            {context}


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
        """

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
            *Task: Implement the original webpage creation task*
            ```webpage_details
            {webpage_idea}
            ```end_webpage_details

            **Important Details:**
            1. All necessary imports and libraries are at the top of each file
            2. Each code block is preceded by a file path where it should be placed
            3. Code is organized logically
            4. Resolve duplicate and conflicting code with discretion
            5. Only code and file paths are returned

            **Example Output:**
            app.py
            ```python
            def foo():
                pass
            ```

            templates/home.html
            ```html
            <!DOCTYPE html>
            ```
            
            static/style.css
            ```css
                /* Foo */
            ```
            
            **Integrate the following components to implement the webpage**
                ***Components:***
                {components}
            """.format(
            webpage_idea=webpage_idea, components="".join(prev_components)
        )
        CLIClient.emit("Integrate components:\n" + out_str)
        return out_str

    @Operator.qna
    def implement_html_element(self, prompt: str) -> str:
        out_str = f"""
        Generate an html element with the following description:\n
        {prompt}

        Example 1.
        Description: Create a header that says `Title`
        Output: <h1>Title</h1>

        Example 2.
        Description: Create an input form with a submit button
        Output:<form method="POST" action="/">
        <label for="textInput">Input:</label>
        <input type="text" id="textInput" name="textInput" required>
        <button type="submit">Submit</button>
        </form>
        """
        CLIClient.emit("implement_html_element " + out_str)
        return out_str


class Executive(Operator):
    """
    Represents an Operator that instructs and guides other Operators.
    """

    @Operator.qna
    def plan_components(self, starting_prompt) -> str:
        return """\
        List the essential code components required to implement the project idea. Each component should be atomic,\
        such that a developer could implement it in isolation provided placeholders for preceding components.
        
        Your response must:
        1. Focus on the conceptual steps of specific code elements or function calls
        2. Be comprehensive, accurate, and complete; cover all necessary components
        3. Use technical terms appropriate for the specific programming language and framework.
        4. Sequence components logically, with later components dependent on previous ones
        5. Put each component on a new line without numbering

        Assumptions:
        - Assume all dependencies are already installed but NOT imported.

        Example format:
        [Natural language specification of the specific code component or function call]
        [Natural language specification of the specific code component or function call]
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
        return f"""Provide an explicit summary of what has been implemented as a list of points.

        Previous Components: {summary}
        Current Component Implementation: {implementation}

        For each component summary:
        1. Describe its functionality using natural language
        2. Include file name, function name, and variable name in the description.

        Example:
        1. Imported the packages numpy as np, and pandas as pd in app.py
        2. Instantiated a pandas dataframe named foo, with column names bar and baz in app.py
        3. Populated foo with random ints in app.py
        4. Printed average of bar and baz in the main function of app.py
        """


class AWSOperator:
    """
    Represents an Operator that takes finalized code, and deploys it to AWS
    """

    def __init__(self):
        self.SHARED_VOLUME: str = "/shared"
        self.DIND_BUILDER_HOST: str = "dind-builder"
        self.DIND_BUILDER_PORT: int = 5000

    def deploy(self, backend_code: str, project_uuid: UUID):
        """
        Creates and puts a docker image with backend_code + server launch logic into AWS ECR.
        Launches a task with that docker image.
        """
        build_dir_name = f"so_{project_uuid}"
        build_dir_path = os.path.join(self.SHARED_VOLUME, build_dir_name)

        os.makedirs(build_dir_path, exist_ok=True)
        dockerfile_content = dedent(
            f"""
            FROM python:3.11.9-slim-bookworm
            WORKDIR /app
            RUN pip install flask concrete-operators
            COPY . .
            ENV OPENAI_API_KEY {os.environ['OPENAI_API_KEY']}
            CMD ["flask", "run", "--host=0.0.0.0", "--port=80"]
            """
        )
        start_script = dedent(
            """
            #!/bin/sh
            set -e
            if ! command -v flask &> /dev/null
            then
                echo "Flask is not installed. Installing..."
                pip install flask
            fi

            if ! pip show concrete-operators &> /dev/null
            then
                echo "concrete-operators is not installed. Installing..."
                pip install concrete-operators
            fi

            if [ -z "$OPENAI_API_KEY" ]
            then
                echo "Error: OPENAI_API_KEY is not set. Please set it before running this script."
                exit 1
            fi
            flask run --host=0.0.0.0 --port=80
            """
        )
        # writes app.py and other files to build_dir_path
        self.parse_and_write_files(backend_code, build_dir_path)
        with open(os.path.join(build_dir_path, "Dockerfile"), "w") as f:
            f.write(dockerfile_content)
        with open(os.path.join(build_dir_path, "start.sh"), "w") as f:
            f.write(start_script)

        max_retries = 5
        for _ in range(max_retries):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect((self.DIND_BUILDER_HOST, self.DIND_BUILDER_PORT))
                    s.sendall(build_dir_name.encode())
                break
            except Exception as e:
                print(e)
                time.sleep(5)

        return True

    def parse_and_write_files(self, backend_code: str, build_dir_path: str):
        """
        Splits out multiple code blocks by programming language.
        Assumes one file per filetype or language.
        """
        out_files: dict[str, str] = {}
        file_string_lines = backend_code.strip().split("\n")

        file_start_line, file_name = None, None
        for i, line in enumerate(file_string_lines):
            if line.startswith("```"):
                if file_start_line is None:
                    # New file detected
                    file_name = file_string_lines[i - 1]
                    file_start_line = i + 1
                else:
                    # File is done
                    out_files[file_name] = "\n".join(file_string_lines[file_start_line:i])
                    file_start_line, file_name = None, None

        for file_name, contents in out_files.items():
            file_path = Path(os.path.join(build_dir_path, cast(str, file_name)))
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w") as f:
                f.write(contents)
