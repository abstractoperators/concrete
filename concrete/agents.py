import os
import socket
import time
from functools import wraps
from operator import attrgetter
from pathlib import Path
from textwrap import dedent
from typing import Callable, List, cast
from uuid import UUID, uuid1

from .clients import CLIClient, Client


class Agent:
    """
    Represents the base agent for further implementation
    """

    def __init__(self, clients: dict[str, Client]):
        self.uuid = uuid1()
        self.clients = clients

        # TODO: Move specific software prompting to its own SoftwareAgent class or mixin

    def _qna(
        self,
        question: str,
        # thread: Thread,
        # agent_task: str | None = None,
    ):
        """
        "Question and Answer", given a query, return an answer.

        # Synchronous. Creates a new thread if one isn't given

        user_request: eg) "Create a website that does xyz. Can include context"
        agent_task: eg) "List the components required to make fulfill the users request"
        """
        thread = self.clients["openai"].create_thread()

        # eg) make a website...
        self.clients["openai"].client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=question,
        )

        # eg) list the components required to make fulfill the users request
        self.clients["openai"].client.beta.threads.runs.create_and_poll(
            thread_id=thread.id,
            assistant_id=self.assistant.id,
        )

        messages = self.clients["openai"].client.beta.threads.messages.list(thread_id=thread.id, order="asc")

        # Assume message data is TextContentBlock
        answer = attrgetter("text.value")(messages.data[-1].content[0])

        for i, message in enumerate(messages.data):
            CLIClient.emit(f'\nQNA Message ({i}): ({message.role})\n{message.content[0].text.value}')

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
            # thread = kwargs.pop("thread", None)
            # user_request = dedent(kwargs.pop("user_request", None))
            question = dedent(question_producer(*args, **kwargs))
            return self._qna(question=question)

        return _send_and_await_reply


class Developer(Agent):
    """
    Represents an agent that produces code.
    """

    def __init__(self, clients: dict[str, Client]):
        super().__init__(clients)
        agent_role = (
            "You are an expert software developer. You will follow the instructions given to you to complete each task."
            "You will follow example formatting, defaulting to no formatting if no example is provided."
        )
        self.assistant = self.clients["openai"].create_assistant(
            instructions=agent_role, name="Developer", description="This is a developer assistant"
        )

    @Agent.qna
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

    @Agent.qna
    def implement_component(self, context: str, dedent=True) -> str:
        """
        Prompts the agent to implement a component based off of the components
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

    @Agent.qna
    def integrate_components(
        self,
        planned_components: List[str],
        implementations: List[str],
        webpage_idea: str,
    ) -> str:
        """
        Prompts agent to combine code implementations of multiple components
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

    @Agent.qna
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


class Executive(Agent):
    """
    Represents an agent that instructs and guides other agents.
    """

    def __init__(self, clients: dict[str, Client]):
        super().__init__(clients)
        agent_role = (
            "You are an expert executive software developer."
            "You will follow the instructions given to you to complete each task."
        )
        self.assistant = self.clients["openai"].create_assistant(
            instructions=agent_role, name="Executive", description="This is an executive assistant"
        )

    @Agent.qna
    def plan_components(self, user_request) -> str:
        return """\
        List the essential, atomic components needed to fulfill the user's request.
        Use your discretion as a expert developer, and provide a comprehensive, declarative list of components.
        
        Your responses must:
        1. Include specific components
        2. Be comprehensive, accurate, and complete
        3. Use technical terms appropriate for the specific programming language and framework.
        4. Sequence components logically, with later components dependent on previous ones
        5. Put each component on a new line without numbering
        6. Assume all dependencies are already installed but NOT imported.

        Example format:
        [Natural language specification of the specific code component or function call]
        [Natural language specification of the specific code component or function call]
        ...
        
        User Request: {user_request}
        """.format(
            user_request=user_request
        )

    @Agent.qna
    def answer_question(self, context: str, question: str) -> str:
        """
        Prompts the agent to answer a question
        Returns the answer
        """
        return (
            f"Context: {context} Developer's Question: {question}\n "
            "As the senior advisor, answer with specificity the developer's question about this component. "
            "If there is no question, then respond with 'Okay'. Do not provide clarification unprompted."
        )

    @Agent.qna
    def generate_summary(self, summary: str, implementation: str) -> str:
        """
        Generates a summary of completed components
        Returns the summary
        """

        prompt = """\
        Add a summary of the current component implementation to the existing summary of components (if any).
        Return only the list.
        For each component summary:
        1. Describe its full functionality using natural language.
        2. Include file name, function name, and variable name in the description.

        Example Output:
        1. Imported the packages numpy as np, and pandas as pd in app.py
        2. Instantiated a pandas dataframe named foo, with column names bar and baz in app.py
        3. Populated foo with random ints in app.py
        4. Printed average of bar and baz in the main function of app.py
        """
        if summary:
            prompt += f"\nPrevious Components Summarized: \n{summary}"
        prompt += f"\nCurrent Component Implementation: \n{implementation}"
        return prompt


class AWSAgent:
    """
    Represents an agent that takes finalized code, and deploys it to AWS
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
            # RUN pip install flask concrete-operators
            COPY . .
            ENV OPENAI_API_KEY {os.environ['OPENAI_API_KEY']}
            ENV OPENAI_TEMPERATURE 0
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
            print(f"Writing to {os.path.join(build_dir_path, file_name)}")
            file_path = Path(os.path.join(build_dir_path, cast(str, file_name)))
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w") as f:
                f.write(contents)
