import json
from collections.abc import AsyncGenerator
from textwrap import dedent
from typing import Optional
from uuid import uuid1

from . import prompts
from .abstract import AbstractOperator_co
from .clients import Client_con, OpenAIClient
from .models.messages import (
    PlannedComponents,
    ProjectDirectory,
    ProjectFile,
    Summary,
    TextMessage,
    Tool,
)
from .operators import Developer, Executive
from .state import ProjectStatus, State
from .tools import AwsTool, invoke_tool


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
        clients: dict[str, Client_con],
        deploy: bool = False,
        use_celery: bool = True,
    ):
        self.state = State(self, orchestrator=orchestrator)
        self.uuid = uuid1()  # suffix is unique based on network id
        self.clients = clients
        self.starting_prompt = starting_prompt
        self.exec = exec
        self.dev = dev
        self.exec = exec
        self.dev = dev
        self.orchestrator = orchestrator
        self.results = None
        self.update(status=ProjectStatus.READY)
        self.deploy = deploy
        self.use_celery = use_celery

    def do_work(self) -> AsyncGenerator[tuple[str, str], None]:
        """
        Break down prompt into smaller components and write the code for each individually.
        """
        self.update(status=ProjectStatus.WORKING)
        if self.use_celery:
            return self._do_work_celery()
        return self._do_work_plain()

    async def _do_work_plain(self) -> AsyncGenerator[tuple[str, str], None]:
        planned_components_resp: PlannedComponents = self.exec.plan_components(
            self.starting_prompt, message_format=PlannedComponents
        )  # type: ignore
        components: list[str] = planned_components_resp.components
        yield Executive.__name__, "\n".join(components)

        summary = ""
        all_implementations = []
        for component in components:
            # Use communicative_dehallucination for each component
            async for agent_or_implementation, message in communicative_dehallucination(
                self.exec,
                self.dev,
                summary,
                component,
                starting_prompt=self.starting_prompt,
                max_iter=0,
            ):
                if agent_or_implementation in (Developer.__name__, Executive.__name__):
                    yield agent_or_implementation, message
                else:  # last result
                    all_implementations.append(agent_or_implementation)
                    summary = message

        files: ProjectDirectory = self.dev.integrate_components(  # type: ignore
            components,
            all_implementations,
            self.starting_prompt,
            message_format=ProjectDirectory,
        )

        if self.deploy:
            # TODO Use an actual DB instead of emulating one with a dictionary
            # TODO Figure something out safer than eval
            yield "executive", "Deploying to AWS"
            AwsTool.results.update({files.project_name: json.loads(files.__repr__())})

            deploy_tool_call: Tool = self.dev.chat(
                f"""Deploy the provided project to AWS. The project directory is: {files}""",
                tools=[AwsTool],
                message_format=Tool,
            )  # type: ignore
            invoke_tool(**deploy_tool_call.model_dump())  # dict() is deprecated

        self.update(status=ProjectStatus.FINISHED)
        yield Developer.__name__, str(files)

    # TODO: implement using Celery task calls
    async def _do_work_celery(self) -> AsyncGenerator[tuple[str, str], None]:
        planned_components_resp: PlannedComponents = (
            self.exec.plan_components.delay(
                starting_prompt=self.starting_prompt, message_format=PlannedComponents
            ).get()
        ).message
        components: list[str] = planned_components_resp.components

        yield Executive.__name__, "\n".join(components)

        summary = ""
        all_implementations = []
        for component in components:
            # Use communicative_dehallucination for each component
            async for agent_or_implementation, message in communicative_dehallucination(
                self.exec,
                self.dev,
                summary,
                component,
                starting_prompt=self.starting_prompt,
                max_iter=0,
                celery=True,
            ):
                if agent_or_implementation in (Developer.__name__, Executive.__name__):
                    yield agent_or_implementation, message
                else:  # last result
                    all_implementations.append(agent_or_implementation)
                    summary = message
        files: ProjectDirectory = (
            self.dev.integrate_components.delay(
                planned_components=components,
                implementations=all_implementations,
                idea=self.starting_prompt,
                message_format=ProjectDirectory,
            ).get()
        ).message

        if self.deploy:
            # TODO Use an actual DB instead of emulating one with a dictionary
            yield "executive", "Deploying to AWS"
            AwsTool.results.update({files.project_name: json.loads(files.__repr__())})

            deploy_tool_call: Tool = self.dev.chat.delay(
                message=f"Deploy the provided project to AWS. The project directory is: {files}",
                tools=[AwsTool],
                message_format=Tool,
            ).message

            invoke_tool(**deploy_tool_call.dict())

        self.update(status=ProjectStatus.FINISHED)
        yield Developer.__name__, str(files)


class Orchestrator:
    pass


class SoftwareOrchestrator(Orchestrator, StatefulMixin):
    """
    An Orchestrator is a set of configured Operators and a resource manager.

    Provides a single entry point for common interactions with Operators
    """

    def __init__(self):
        self.state = State(self, orchestrator=self)
        self.uuid = uuid1()
        self.clients = {
            "openai": OpenAIClient(),
        }
        self.operators: dict[str, AbstractOperator_co] = {
            "exec": Executive(self.clients),
            "dev": Developer(self.clients),
        }
        self.update(status=ProjectStatus.READY)

    def process_new_project(
        self, starting_prompt: str, deploy: bool = False, use_celery: bool = True
    ) -> AsyncGenerator[tuple[str, str], None]:
        self.update(status=ProjectStatus.WORKING)
        current_project = SoftwareProject(
            starting_prompt=starting_prompt.strip() or prompts.HELLO_WORLD_PROMPT,
            exec=self.operators["exec"],
            dev=self.operators["dev"],
            orchestrator=self,
            clients=self.clients,
            deploy=deploy,
            use_celery=use_celery,
        )
        return current_project.do_work()


async def communicative_dehallucination(
    executive: Executive,
    developer: Developer,
    summary: str,
    component: str,
    max_iter: int = 1,
    starting_prompt: Optional[str] = None,
    celery: bool = False,
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
    if starting_prompt:
        context = f"Starting Prompt:\n{starting_prompt}\n{context}"

    yield Executive.__name__, component
    # Iterative Q&A process
    q_and_a = []
    for _ in range(max_iter):
        if celery:
            question: TextMessage = developer.ask_question.delay(context=context).get().message
        else:
            question: TextMessage = developer.ask_question(context)  # type: ignore

        if question == "No Question":
            break

        yield Developer.__name__, question.text

        if celery:
            answer: TextMessage = executive.answer_question.delay(context=context, question=question).get().message
        else:
            answer: TextMessage = executive.answer_question(context, question)  # type: ignore
        q_and_a.append((question, answer))

        yield Executive.__name__, answer.text

    if q_and_a:
        context += "\nComponent Clarifications:"
        for question, answer in q_and_a:
            context += f"\nQuestion: {question}"
            context += f"\nAnswer: {answer}"

    if celery:
        implementation: ProjectFile = (
            developer.implement_component.delay(context=context, message_format=ProjectFile).get().message
        )
    else:
        implementation: ProjectFile = developer.implement_component(context, message_format=ProjectFile)  # type: ignore

    yield Developer.__name__, str(implementation)

    if celery:
        new_summary: Summary = (
            executive.generate_summary.delay(
                summary=summary,
                implementation=str(implementation),
                message_format=Summary,
            )
            .get()
            .message
        )  # type: ignore
    else:
        new_summary: Summary = executive.generate_summary(  # type: ignore
            summary, str(implementation), message_format=Summary
        ).summary

    yield Executive.__name__, str(new_summary)
    yield Executive.__name__, str(implementation)
