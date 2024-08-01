import os
import socket
from functools import wraps
from operator import attrgetter
from textwrap import dedent
from time import time
from typing import Callable, List
from uuid import uuid1

from openai.types.beta.thread import Thread

from .clients import Client


class Agent:
    """
    Represents the base agent for further implementation
    """

    auto_dedent = True

    def __init__(self, clients: dict[str, Client]):
        self.uuid = uuid1()
        self.clients = clients

        # TODO: Move specific software prompting to its own SoftwareAgent class or mixin
        instructions = (
            "You are a software developer. " "You will answer software development questions as concisely as possible."
        )
        self.assistant = self.clients["openai"].create_assistant(prompt=instructions)  # type: ignore

    def _qna(self, content: str, thread: Thread | None, instructions: str | None = None):
        """
        "Question and Answer", given a query, return an answer.

        Synchronous. Creates a new thread if one isn't given
        """
        thread = thread or self.clients["openai"].create_thread()
        self.clients["openai"].client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=content,
        )
        self.clients["openai"].client.beta.threads.runs.create_and_poll(
            thread_id=thread.id,
            assistant_id=self.assistant.id,
            instructions=instructions,
        )

        messages = self.clients["openai"].client.beta.threads.messages.list(thread_id=thread.id, order="desc", limit=1)
        # Assume message data is TextContentBlock
        answer = attrgetter("text.value")(messages.data[0].content[0])
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
            thread = kwargs.pop("thread", None)
            instructions = kwargs.pop("instructions", None)
            content = message_producer(*args, **kwargs)
            content = dedent(content) if self.auto_dedent else content
            return self._qna(content, thread=thread, instructions=instructions)

        return _send_and_await_reply


class Developer(Agent):
    """
    Represents an agent that produces code.
    """

    @Agent.qna
    def ask_question(self, context: str) -> str:
        """
        Accept instructions and ask a question about it if necessary.

        Can return `no question`.
        """
        return f"""Context:
            {context}

            If necessary, ask one essential question for continued implementation. If unnecessary, respond 'No Question'.

            Example:
            Context:
            1. Imported the Flask module from the flask package
            Current Component: Create a Flask application instance
            Clarification: None

            No Question


            Example:
            Context:
            1. The code imported the Flask module from the flask package
            2. The code created a Flask application named "app"
            3. Created a route for the root URL ('/')
            Current Component: Create a function that will be called when the root URL is accessed. This function should return HTML with a temporary Title, Author, and Body Paragraph

            What should the function be called?"""  # noqa: E501

    @Agent.qna
    def implement_component(self, context: str, dedent=True) -> str:
        """
        Prompts the agent to implement a component based off of the components context
        Returns the code for the component
        """
        return f"""
            Context:
            {context}

            Based on the context, provide code the current component. Never provide unspecified code.

            Example:
            Context:
            1. Imported the Flask module from the flask package
            Current Component: Create a flask application instance named 'app'
            Clarification: None

            app = Flask(app)


            Example:
            Context:
            1. The code imported the Flask module from the flask package
            2. The code created a Flask application named "app"
            3. Created a route for the root URL ('/')
            Current Component: Create a function that will be called when the root URL is accessed. This function should return HTML with a temporary Title, Author, and Body Paragraph.
            Clarification: The function should be called index

            def index():
                return '''
                <!DOCTYPE html>
                <html>
                    <head>
                        <title>Page Title</title>
                    </head># noqa: E501
                <body>
                    <h1>Main Title</h1>
                    <h2>Authors:</h2>
                    <p>Author 1, Author 2</p>
                    <p>This is a body paragraph.</p>
                </body>
                </html>'''
        """  # noqa: E501

    @Agent.qna
    def integrate_components(self, implementations: List[str], webpage_idea: str) -> str:
        """
        Prompts agent to combine code implementations of multiple components
        Returns the combined code
        """
        return (
            "\nTask: Combine all these implementations into a single, coherent final application to "
            f"""{webpage_idea}
            
            Ensure that:
            1. All necessary imports are at the top of the file
            2. Code is organized logically
            3. There are no duplicate or conflicting code
            4. Resolve conflicting or redundant pieces of code.
            5. Only code is returned
            """
        )
        # Below at end of prompt was messing things up
        # """
        # Implementations:
        # {chr(92) + "n".join([f"{i}. " + piece for i, piece in enumerate(implementations)])}
        # """


class Executive(Agent):
    """
    Represents an agent that instructs and guides other agents.
    """

    @Agent.qna
    def plan_components(self) -> str:
        return """
        List, in natural language, only the essential code components needed to fulfill the user's request.
 
        Your response must:
        1. Include only core components.
        2. Put each new component on a new line (not numbered, but conceptually sequential).
        3. Focus on the conceptual steps of specific code elements or function calls
        4. Be comprehensive, covering all necessary components
        5. Use technical terms appropriate for the specific programming language and framework.
        6. Naturally sequence components, so that later components are dependent on previous ones.
 
        Important:
        - Assume all dependencies are already installed but not imported.
        - Do not include dependency installations.
        - Focus solely on the code components needed to implement the functionality.
        - NEVER provide code example
        - ALWAYS ensure all necessary components are present
 
        Example format:
        [Natural language specification of the specific code component or function call]
        [Natural language specification of the specific code component or function call]
        ...
        """

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
        return f"""Provide an explicit summary of what has been implemented as a list of points.

        Previous Components: {summary}
        Current Component Implementation: {implementation}

        For each component:
        1. Describe its functionality if necessary
        2. Include variable names if necessary
        3. Provide implementation details using natural language

        Example:
        1. imported the packages numpy and pandas as np and pd respectively. imported random
        2. Instantiated a pandas dataframe named foo, with column names bar and baz
        3. Populated foo with random ints
        4. Printed average of bar and baz
        """


class AWSAgent:
    """
    Represents an agent that takes finalized code, and deploys it to AWS
    """

    def __init__(self):
        self.SHARED_VOLUME = "/shared"
        self.DIND_BUILDER_HOST = "dind-builder"
        self.DIND_BUILDER_PORT = 5000

    def deploy(self, backend_code, client_id, project_uuid):
        """
        Creates and puts a docker image with backend_code + server launch logic into AWS ECR.
        Launches a task with that docker image.
        """
        build_dir_name = f"so_uuid_{project_uuid}"
        build_dir_path = os.path.join(self.SHARED_VOLUME, build_dir_name)

        os.makedirs(build_dir_path, exist_ok=True)
        dockerfile_content = dedent(
        """
        FROM python:3.11.9-slim-bookworm
        WORKDIR /app
        RUN pip install flask
        COPY . .
        CMD ["flask", "run", "--host=0.0.0.0", "--port=80"]
        """
        )

        with open(os.path.join(build_dir_path, "app.py"), "w") as f:
            f.write(backend_code)
        with open(os.path.join(build_dir_path, "Dockerfile"), "w") as f:
            f.write(dockerfile_content)

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
