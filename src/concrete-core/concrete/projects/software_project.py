import json
from collections.abc import AsyncGenerator
from textwrap import dedent
from uuid import uuid1

from concrete.clients import LMClient_con
from concrete.models.messages import (
    PlannedComponents,
    ProjectDirectory,
    ProjectFile,
    Summary,
    TextMessage,
    Tool,
)
from concrete.operators import Developer, Executive
from concrete.orchestrators import Orchestrator
from concrete.state import ProjectStatus, State, StatefulMixin
from concrete.tools.aws import AwsTool
from concrete.tools.utils import invoke_tool


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
        clients: dict[str, LMClient_con],
        deploy: bool,
        run_async: bool,
    ):
        self.state = State(self, orchestrator=orchestrator)
        self.uuid = uuid1()  # suffix is unique based on network id
        self.clients = clients
        self.starting_prompt = starting_prompt
        self.exec = exec
        self.dev = dev
        self.orchestrator = orchestrator
        self.results = None
        self.update(status=ProjectStatus.READY)
        self.deploy = deploy
        self.run_async = run_async

    async def do_work(self) -> AsyncGenerator[tuple[str, str], None]:
        """
        Break down prompt into smaller components and write the code for each individually.
        """
        self.update(status=ProjectStatus.WORKING)

        planned_components_resp: PlannedComponents = self.exec.plan_components(
            self.starting_prompt,
            options={
                "response_format": PlannedComponents,
                "run_async": self.run_async,
            },
        )  # type: ignore
        if self.run_async:
            planned_components_resp = planned_components_resp.get().message
        components: list[str] = planned_components_resp.components
        yield Executive.__name__, str(planned_components_resp)

        summary = ""
        all_implementations = []
        for component in components:
            # Use communicative_dehallucination for each component
            async for agent_or_implementation, message in communicative_dehallucination(
                self.exec,
                self.dev,
                summary,
                component,
                self.run_async,
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
            options={
                "response_format": ProjectDirectory,
                "run_async": self.run_async,
            },
        )
        if self.run_async:
            files = files.get().message

        if self.deploy:
            # TODO Use an actual DB instead of emulating one with a dictionary
            # TODO Figure something out safer than eval
            yield "executive", "Deploying to AWS"
            AwsTool.results.update({files.project_name: json.loads(files.__repr__())})

            deploy_tool_call: Tool = self.dev.chat(
                f"""Deploy the provided project to AWS. The project directory is: {files}""",
                options={
                    "tools": [AwsTool],
                    "response_format": Tool,
                },
            )  # type: ignore
            invoke_tool(**deploy_tool_call.model_dump())  # dict() is deprecated

        self.update(status=ProjectStatus.FINISHED)
        yield Developer.__name__, str(files)


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
        question: TextMessage = developer.ask_question(context, options=run_async_kwarg).get()
        if run_async:
            question = question.get()

        if question == "No Question":
            break

        yield Developer.__name__, question.text

        answer: TextMessage = executive.answer_question(context, question, options=run_async_kwarg)  # type: ignore
        if run_async:
            answer = answer.get()
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
        implementation = implementation.get()

    yield Developer.__name__, str(implementation)

    new_summary: Summary = executive.generate_summary(  # type: ignore
        summary,
        str(implementation),
        options=run_async_kwarg | {"response_format": Summary},
    )
    if run_async:
        new_summary = new_summary.get()
    else:
        new_summary = new_summary.summary  # type: ignore

    yield Executive.__name__, str(new_summary)

    # TODO: synchronize message persistence and websocket messages
    # yield Executive.__name__, str(implementation)
