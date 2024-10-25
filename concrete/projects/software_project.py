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
from concrete.state import ProjectStatus, State, StatefulMixin
from concrete.tools import AwsTool, invoke_tool


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
