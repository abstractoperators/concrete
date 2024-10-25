import json
from collections import defaultdict
from collections.abc import AsyncGenerator
from textwrap import dedent
from typing import Any, Callable
from uuid import UUID, uuid1, uuid4

from concrete import prompts
from concrete.clients import Client_con, OpenAIClient
from concrete.models.messages import (
    PlannedComponents,
    ProjectDirectory,
    ProjectFile,
    Summary,
    TextMessage,
    Tool,
)
from concrete.operators import Developer, Executive, Operator
from concrete.projects import SoftwareProject
from concrete.state import ProjectStatus, State, StatefulMixin
from concrete.tools import AwsTool, invoke_tool

from . import Orchestrator


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
        self.update(status=ProjectStatus.READY)
        self.operators = {'exec': Executive(self.clients), 'dev': Developer(self.clients)}

    def add_operator(self, operator: Operator, title: str) -> None:
        self.operators[title] = operator

    def process_new_project(
        self,
        starting_prompt: str,
        project_id: UUID = uuid4(),
        deploy: bool = False,
        run_async: bool = False,
        exec: str | None = None,
        dev: str | None = None,
    ) -> AsyncGenerator[tuple[str, str], None]:
        """
        exec (str): Name of operator in self.operators to use as exec
        dev (str): Name of operator in self.operators to use as dev
        """
        if exec is not None and exec not in self.operators:
            raise ValueError(f"{exec} not found.")
        if dev is not None and dev not in self.operators:
            raise ValueError(f"{dev} not found.")

        exec_operator: Executive = self.operators[exec] if exec is not None else self.operators['exec']
        dev_operator: Developer = self.operators[dev] if dev is not None else self.operators['dev']

        self.update(status=ProjectStatus.WORKING)

        current_project = SoftwareProject(
            starting_prompt=starting_prompt.strip() or prompts.HELLO_WORLD_PROMPT,
            exec=exec_operator,
            dev=dev_operator,
            orchestrator=self,
            clients=self.clients,
            deploy=deploy,
            run_async=run_async,
        )
        return current_project.do_work()


async def communicative_dehallucination(
    executive: Executive,
    developer: Developer,
    summary: str,
    component: str,
    run_async: bool,
    max_iter: int = 1,
    starting_prompt: str | None = None,
) -> AsyncGenerator[tuple[str, str], None]:
    """
    Implements a communicative dehallucination process for software development.

    Args:
        executive (Executive): The executive assistant object for answering questions.
        developer (Developer): The developer assistant object for asking questions and implementing.
        summary (str): A summary of previously implemented components.
        component (str): The current component to be implemented.
        run_async (bool): Whether to complete process via Celery calls.
        starting_prompt (str, default = None): The initial prompt for the project.
        max_iter (int, default = 1): Maximum number of Q&A iterations.

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

    # TODO: synchronize message persistence and websocket messages
    # yield Executive.__name__, component
    # Iterative Q&A process

    # TODO: Test out makefile helloworld, saas, and celery helloworld?
    run_async_kwarg = {"run_async": run_async}
    q_and_a = []
    for _ in range(max_iter):
        question: TextMessage = developer.ask_question(context, options=run_async_kwarg).get().message
        if run_async:
            question = question.get().message

        if question == "No Question":
            break

        yield Developer.__name__, question.text

        answer: TextMessage = executive.answer_question(context, question, options=run_async_kwarg)  # type: ignore
        if run_async:
            answer = answer.get().message
        q_and_a.append((question, answer))

        yield Executive.__name__, answer.text

    if q_and_a:
        context += "\nComponent Clarifications:"
        for question, answer in q_and_a:
            context += f"\nQuestion: {question}"
            context += f"\nAnswer: {answer}"

    implementation: ProjectFile = developer.implement_component(  # type: ignore
        context,
        options=run_async_kwarg | {"response_format": ProjectFile},
    )
    if run_async:
        implementation = implementation.get().message

    yield Developer.__name__, str(implementation)

    new_summary: Summary = executive.generate_summary(  # type: ignore
        summary,
        str(implementation),
        options=run_async_kwarg | {"response_format": Summary},
    )
    if run_async:
        new_summary = new_summary.get().message
    else:
        new_summary = new_summary.summary  # type: ignore

    yield Executive.__name__, str(new_summary)

    # TODO: synchronize message persistence and websocket messages
    # yield Executive.__name__, str(implementation)
