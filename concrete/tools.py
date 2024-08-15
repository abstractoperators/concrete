"""
srry for indentation, black is complaining about lines being too long.

Tools for integration with OpenAI's Structured Outputs.
Use: Add tools to a function to inform the operator of available tools.
    1) Tell operator what tools are available
    2) TODO: Update qna output to include tool(s) field.
        a) ATM, all responses inherit from Tools class.
           This is good, but we only want the outermost response to have a tools field.
        eg) ProjectFile inherits from Tools, and so does ProjectDirectory.
        ProjectDirectory should have a list of ProjectFiles, but we only want ProjectDirectory to have tools.
    3) TODO: If tools field is present and populated, hit the response tool_call field with eval() to execute the tool.
    4) TODO: Update prompting to get good tool call behavior.

Example:
In this example, TestTool is an example Tool that can be provided to an operator qna.
Tools should have syntax documented in their docstrings so they are made available to the operator.
Operator qna functions should have a tools parameter.
This takes a list of tools [TestTool] (objects, not instances) that are available to the operator.
TODO: Move available tools query to decorator instead of functions decorated with qna.

class TestTool(metaclass=ToolClass):
    @classmethod
    def test(cls, idk: str, another: int = 5) -> str:
        '''idk: (Description of idk goes here)
        another: (Description of another goes here)
        Returns a string
        '''
        return f"Tested {idk}!"

    def another_method(self):
        pass


class testOperator(operators.Operator):
    def __init__(
        self,
        clients={'openai': OpenAIClient()},
        instructions=("You are a software developer. You will answer completely, concisely, and accurately."
        "When provided tools, you will first answer, then use tools to complete the task."),
    ):
        super().__init__(clients, instructions)

    @operators.Operator.qna
    def use_tools(self, question, tools: List[type]):

        query = ""
        if tools:
            query += '''Here are your available tools:\
                Either call the tool with its specified syntax, or leave its field blank.\n'''
            for tool in tools:
                query += str(tool)

        query += '''\n\n{question}'''.format(question=question)
        return query
"""

import inspect
import os
from textwrap import dedent

from .operator_responses import ProjectDirectory


class MetaTool(type):
    """
    This metaclass enables dynamic string representation of class objects without needing to instantiate them.
    """

    def __new__(cls, name, bases, attrs):
        method_info = []
        for attr, value in attrs.items():
            if attr.startswith("__"):
                continue
            if callable(value) or isinstance(value, (classmethod, staticmethod)):
                func = value.__func__ if isinstance(value, (classmethod, staticmethod)) else value

                docstring = func.__doc__.strip() if func.__doc__ else "No docstring provided"

                signature = inspect.signature(func)
                params = []
                for param_name, param in signature.parameters.items():
                    param_str = param_name
                    if param.annotation != inspect.Parameter.empty:
                        param_str += f": {param.annotation.__name__}"
                    if param.default != inspect.Parameter.empty:
                        param_str += f" = {param.default}"
                    params.append(param_str)

                return_str = (
                    f" -> {signature.return_annotation.__name__}"
                    if signature.return_annotation != inspect.Signature.empty
                    and signature.return_annotation is not None
                    else ""
                )

                method_signature = f"{attr}({', '.join(params)}){return_str}"
                method_info.append(f"{method_signature}\n\t{docstring}")

        attrs['_str_representation'] = f"{name} Tool with methods:\n" + "\n".join(
            f"   - {info}" for info in method_info
        )
        return super().__new__(cls, name, bases, attrs)

    def __str__(cls):
        return cls._str_representation

    def __repr__(cls):
        return str(cls)


class DeployToAWS(metaclass=MetaTool):
    SHARED_VOLUME = "/shared"

    def deploy_to_aws(self, project_directory: ProjectDirectory, project_name: str):
        """
        project_directory (ProjectDirectory): An object containing the project's files.
        """
        build_dir_path = os.path.join(self.SHARED_VOLUME, project_name)
        os.makedirs(build_dir_path, exist_ok=True)

        dockerfile_content = dedent(
            f"""
            FROM python:3.11.9-slim-bookworm
            WORKDIR /app
            RUN pip install flask concrete-operators
            COPY . .
            ENV OPENAI_API_KEY={os.environ['OPENAI_API_KEY']}
            ENV OPENAI_TEMPERATURE=0
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

        with open(os.path.join(build_dir_path, "Dockerfile"), "w") as f:
            f.write(dockerfile_content)
        with open(os.path.join(build_dir_path, "start.sh"), "w") as f:
            f.write(start_script)

        for project_file in project_directory.files:
            file_path = os.path.join(build_dir_path, project_file.file_name)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w") as f:
                f.write(project_file.file_contents)
