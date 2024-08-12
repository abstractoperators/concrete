from textwrap import dedent
from typing import Tuple
from uuid import uuid1

from . import prompts
from .clients import CLIClient, Client, OpenAIClient
from .operators import (
    AWSOperator,
    Developer,
    Executive,
    PlannedComponents,
    ProjectDirectory,
    ProjectFile,
    Summary,
)
from .state import ProjectStatus, State


class StatefulMixin:
    def update(self, **kwargs):
        self.state.data.update(kwargs)
        if kwargs.get("status") == ProjectStatus.FINISHED:
            self.state.data["completed"] = True


class SoftwareProject(StatefulMixin):
    """
    Tracks the execution of a task or objectives
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
        self.clients = clients
        self.starting_prompt = starting_prompt
        self.exec = exec
        self.dev = dev
        self.aws = aws
        self.orchestrator = orchestrator
        self.results = None
        self.update(status=ProjectStatus.READY)
        self.deploy = deploy

    def do_work(self) -> str:
        """
        Break down prompt into smaller components and write the code for each individually.
        """
        self.update(status=ProjectStatus.WORKING, actor=self.exec)

        components = self.plan()
        for component in components:
            CLIClient.emit(f"[Planned Component]: {component}")

        summary = ""
        all_implementations = []
        for component in components:
            # Use communicative_dehallucination for each component
            implementation, summary = communicative_dehallucination(
                self.exec,
                self.dev,
                summary,
                component,
                max_iter=0,
            )

            # Add the implementation to our list
            all_implementations.append(implementation)

        files = self.dev.integrate_components(
            components, all_implementations, self.starting_prompt, response_format=ProjectDirectory
        )

        for project_file in files.files:
            CLIClient.emit(f"\nfile_name: {project_file.file_name}\nfile_contents: {project_file.file_contents}\n")

        self.update(status=ProjectStatus.FINISHED)
        # if self.deploy:
        #     if self.aws is None:
        #         raise ValueError("Cannot deploy without AWSOperator")
        #     final_code_stripped = "\n".join(final_code.strip().split("\n")[1:-1])
        #     cast(AWSOperator, self.aws).deploy(final_code_stripped, self.uuid)

        return files

    def plan(self) -> str:
        planned_components = self.exec.plan_components(self.starting_prompt, response_format=PlannedComponents)
        return planned_components.components


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
        openai_client = OpenAIClient()
        self.clients = {
            "openai": openai_client,
        }
        self.operators = {
            "exec": Executive(self.clients),
            "dev": Developer(self.clients),
            "aws": AWSOperator(),
        }
        self.update(status=ProjectStatus.READY)

    def process_new_project(self, starting_prompt: str, deploy: bool = False):
        self.update(status=ProjectStatus.WORKING)
        current_project = SoftwareProject(
            starting_prompt=starting_prompt or prompts.HELLO_WORLD_PROMPT,
            exec=self.operators["exec"],
            dev=self.operators["dev"],
            aws=self.operators["aws"],
            orchestrator=self,
            clients=self.clients,
            deploy=deploy,
        )
        final_code = current_project.do_work()
        self.update(status=ProjectStatus.FINISHED)
        return final_code


def communicative_dehallucination(
    executive: Executive,
    developer: Developer,
    summary: str,
    component: str,
    max_iter: int = 1,
) -> Tuple[str, str]:
    """
    Implements a communicative dehallucination process for software development.

    Args:
        executive (Executive): The executive assistant object for answering questions.
        developer (Developer): The developer assistant object for asking questions and implementing.
        summary (str): A summary of previously implemented components.
        component (str): The current component to be implemented.
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

    # Iterative Q&A process
    q_and_a = []
    for i in range(max_iter):
        question = developer.ask_question(context)
        CLIClient.emit(f"Developer's question:\n {question}\n")

        if question == "No Question":
            break

        answer = executive.answer_question(context, question)
        CLIClient.emit(f"Executive's answer:\n {answer}\n")

        q_and_a.append((question, answer))
        # Update context with new Q&A pair

    if q_and_a:
        context += "\nComponent Clarifications:"
        for question, answer in q_and_a:
            context += f"\nQuestion: {question}"
            context += f"\nAnswer: {answer}"

    # Developer implements component based on clarified context
    implementation = developer.implement_component(context, response_format=ProjectFile)
    CLIClient.emit(f"Component Implementation:\n{implementation}")

    # Generate a summary of what has been achieved
    summary = executive.generate_summary(summary, implementation, response_format=Summary)
    CLIClient.emit(f"Summary: {summary}").summary

    return implementation, summary
