from textwrap import dedent
from typing import Tuple, cast
from uuid import uuid1

from openai.types.beta.thread import Thread

from . import prompts
from .agents import AWSAgent, Developer, Executive
from .clients import Client, OpenAIClient
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
        aws: AWSAgent | None = None,
        threads: dict[str, Thread] | None = None,  # context -> Thread
        deploy: bool = False,
    ):
        self.state = State(self, orchestrator=orchestrator)
        self.uuid = uuid1()  # suffix is unique based on network id
        self.clients = clients
        self.starting_prompt = starting_prompt
        self.exec = exec
        self.dev = dev
        self.aws = aws
        self.threads = threads or {"main": self.clients["openai"].create_thread()}
        self.orchestrator = orchestrator
        self.results = None
        self.update(status=ProjectStatus.READY)
        self.deploy = deploy

    def do_work(self) -> str:
        """
        Break down prompt into smaller components and write the code for each individually.
        """
        self.update(status=ProjectStatus.WORKING, actor=self.exec)

        orig_components = self.plan(self.starting_prompt)
        components_list = orig_components.split("\n")
        components = [stripped_comp for comp in components_list if (stripped_comp := comp.strip())]

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

        final_code = self.dev.integrate_components(components, all_implementations, self.starting_prompt)

        self.update(status=ProjectStatus.FINISHED)
        if self.deploy:
            if self.aws is None:
                raise ValueError("Cannot deploy without AWSAgent")
            cast(AWSAgent, self.aws).deploy(final_code, self.uuid)

        return final_code

    def plan(self, project_idea) -> str:
        planned_components = self.exec.plan_components(project_idea)
        return planned_components


class Orchestrator:
    pass


class SoftwareOrchestrator(Orchestrator, StatefulMixin):
    """
    An Orchestrator is a set of configured Agents and a resource manager

    Provides a single entry point for common interactions with agents
    """

    def __init__(self):
        self.state = State(self, orchestrator=self)
        self.uuid = uuid1()
        self.clients = {
            "openai": OpenAIClient(),
        }
        self.agents = {
            "exec": Executive(self.clients),
            "dev": Developer(self.clients),
            "aws": AWSAgent(),
        }
        self.update(status=ProjectStatus.READY)

    def process_new_project(self, starting_prompt: str, deploy: bool = False):
        self.update(status=ProjectStatus.WORKING)
        # Immediately spin off a primary thread with the prompt
        threads = {"main": self.clients["openai"].create_thread(starting_prompt)}
        current_project = SoftwareProject(
            starting_prompt=starting_prompt or prompts.HELLO_WORLD_PROMPT,
            exec=self.agents["exec"],
            dev=self.agents["dev"],
            aws=self.agents["aws"],
            orchestrator=self,
            threads=threads,
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
        # CLIClient.emit(f"Developer's question:\n {question}\n")

        if question == "No Question":
            break

        answer = executive.answer_question(context, question)
        # CLIClient.emit(f"Executive's answer:\n {answer}\n")

        q_and_a.append((question, answer))
        # Update context with new Q&A pair

    if q_and_a:
        context += "\nComponent Clarifications:"
        for question, answer in q_and_a:
            context += f"\nQuestion: {question}"
            context += f"\nAnswer: {answer}"

    # Developer implements component based on clarified context
    implementation = developer.implement_component(context)

    # Generate a summary of what has been achieved
    summary = executive.generate_summary(summary, implementation)

    return implementation, summary
