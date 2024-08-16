import json
from collections.abc import AsyncGenerator
from textwrap import dedent
from uuid import uuid1

from . import prompts
from .operator_responses import (
    PlannedComponents,
    ProjectDirectory,
    ProjectFile,
    Summary,
    Tools,
)
from .operators import AWSOperator, Developer, Executive
from .state import ProjectStatus, State
from .tools import AwsTool


class StatefulMixin:
    def update(self, **kwargs):
        self.state.data.update(kwargs)
        if kwargs.get("status") == ProjectStatus.FINISHED:
            self.state.data["completed"] = True


class SoftwareProject(StatefulMixin):
    """
    Tracks the execution of a task or objectives.
    """

    def __init__(
        self,
        starting_prompt: str,
        orchestrator: "Orchestrator",
        exec: Executive,
        dev: Developer,
        clients: dict[str, Client],
        aws: AWSOperator | None = None,
        deploy: bool = False,
    ):
        self.state = State(self, orchestrator=orchestrator)
        self.uuid = uuid1()  # suffix is unique based on network id
        self.starting_prompt = starting_prompt
        self.exec = exec
        self.dev = dev
        self.aws = aws
        self.orchestrator = orchestrator
        self.results = None
        self.update(status=ProjectStatus.READY)
        self.deploy = deploy

    async def do_work(self) -> AsyncGenerator[tuple[str, str], None]:
        """
        Break down prompt into smaller components and write the code for each individually.
        """
        self.update(status=ProjectStatus.WORKING)

        components = executive.plan_components(self.starting_prompt, response_format=PlannedComponents).components
        yield executive.__name__, '\n'.join(components)

        summary = ""
        all_implementations = []
        for component in components:
            # Use communicative_dehallucination for each component
            async for agent_or_implementation, message in communicative_dehallucination(
                summary,
                component,
                starting_prompt=self.starting_prompt,
                max_iter=0,
            ):
                if agent_or_implementation in (Developer.__name__, Executive.__name__):
                    yield agent_or_implementation, str(message)
                else:  # last result
                    all_implementations.append(agent_or_implementation)
                    summary = message

        files = developer.integrate_components(
            components, all_implementations, self.starting_prompt, response_format=ProjectDirectory
        )

        if self.deploy:
            # TODO Use an actual DB instead of emulating one with a dictionary
            # TODO Figure something out safer than eval
            yield "executive", "Deploying to AWS"
            AwsTool.results.update({files.project_name: json.loads(files.__repr__())})

            deploy_tool_call = self.dev.chat(
                f"""Deploy the provided project to AWS. The project directory is: {files}""",
                tools=[AwsTool],
                response_format=Tools,
            )
            for tool in deploy_tool_call.tools:
                full_tool_call = f'{tool.tool_name}.{tool.tool_call}'
                eval(full_tool_call)  # nosec

        self.update(status=ProjectStatus.FINISHED)
        yield developer.__name__, str(files)


class Orchestrator:
    pass


class SoftwareOrchestrator(Orchestrator, StatefulMixin):
    """
    An Orchestrator is a set of configured Operators and a resource manager

    Provides a single entry point for common interactions with Operators
    """

    def __init__(self):
        self.state = State(self, orchestrator=self)
        self.uuid = uuid1()
        self.clients = {
            "openai": OpenAIClient(),
        }
        self.operators = {
            "exec": Executive(self.clients),
            "dev": Developer(self.clients),
        }
        self.aws = AWSOperator()
        self.update(status=ProjectStatus.READY)

    def process_new_project(self, starting_prompt: str, deploy: bool = False) -> AsyncGenerator[tuple[str, str], None]:
        self.update(status=ProjectStatus.WORKING)
        current_project = SoftwareProject(
            starting_prompt=starting_prompt.strip() or prompts.HELLO_WORLD_PROMPT,
            exec=self.operators["exec"],
            dev=self.operators["dev"],
            orchestrator=self,
            aws=self.aws,
            deploy=deploy,
        )
        return current_project.do_work()


async def communicative_dehallucination(
    summary: str,
    component: str,
    starting_prompt: str,
    max_iter: int = 1,
) -> AsyncGenerator[tuple[str, str], None]:
    """
    Implements a communicative dehallucination process for software development.

    Args:
        executive (Executive): The executive assistant object for answering questions.
        developer (Developer): The developer assistant object for asking questions and implementing.
        summary (str): A summary of previously implemented components.
        component (str): The current component to be implemented.
        starting_prompt (str): The initial prompt for the project.
        max_iter (int, optional): Maximum number of Q&A iterations.

    Returns:
        tuple: A tuple containing:
            - implementation (str): The generated implementation of the component.
            - summary (str): A concise summary of what has been achieved.
    """

    context = dedent(
        f"""Previous Components summarized:\n{summary}
    Current Component: {component}"""
    )
    yield executive.__name__, component
    # Iterative Q&A process
    q_and_a = []
    for _ in range(max_iter):
        question = developer.ask_question(context)

        if question == "No Question":
            break

        yield developer.__name__, question.text

        answer = executive.answer_question(context, question)
        q_and_a.append((question, answer))

        yield executive.__name__, answer.text

    if q_and_a:
        context += "\nComponent Clarifications:"
        for question, answer in q_and_a:
            context += f"\nQuestion: {question}"
            context += f"\nAnswer: {answer}"

    # Developer implements component based on clarified context
    implementation = developer.implement_component(context, response_format=ProjectFile)

    yield developer.__name__, str(implementation)

    # Generate a summary of what has been achieved
    summary = executive.generate_summary(summary, implementation, response_format=Summary)

    yield executive.__name__, str(summary)

    yield implementation, str(summary)
