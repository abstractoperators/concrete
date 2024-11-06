from collections.abc import AsyncGenerator
from typing import cast
from uuid import UUID, uuid1, uuid4

from concrete.clients.openai import OpenAIClient
from concrete.operators import Developer, Executive, Operator
from concrete.projects import SoftwareProject
from concrete.state import ProjectStatus, State, StatefulMixin

from concrete import prompts

from . import Orchestrator


class SoftwareOrchestrator(Orchestrator, StatefulMixin):
    """
    An Orchestrator is a set of configured Operators and a resource manager.
    Provides a single entry point for common interactions with Operators
    """

    def __init__(self, store_messages: bool = False):
        self.state = State(self, orchestrator=self)
        self.uuid = uuid1()
        self.clients = {
            "openai": OpenAIClient(),
        }
        self.update(status=ProjectStatus.READY)
        self.operators = {
            "exec": Executive(self.clients, store_messages=store_messages),
            "dev": Developer(self.clients, store_messages=store_messages),
        }

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

        exec_operator: Executive = cast(
            Executive,
            self.operators[exec] if exec is not None else self.operators["exec"],
        )
        dev_operator: Developer = cast(Developer, self.operators[dev] if dev is not None else self.operators["dev"])

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
