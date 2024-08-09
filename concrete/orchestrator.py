import asyncio
from textwrap import dedent
from typing import cast
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

    async def do_work(self):
        """
        Break down prompt into smaller components and write the code for each individually.
        """
        self.update(status=ProjectStatus.WORKING, actor=self.exec)

        orig_components = self.exec.plan_components(self.starting_prompt)
        yield "executive", orig_components
        components_list = orig_components.split("\n")
        components = [stripped_comp for comp in components_list if (stripped_comp := comp.strip())]

        summary = ""
        all_implementations = []
        for component in components:
            # Use communicative_dehallucination for each component
            await asyncio.sleep(0)
            async for agent_or_implementation, message in communicative_dehallucination(
                self.exec,
                self.dev,
                summary,
                component,
                max_iter=0,
            ):
                await asyncio.sleep(0)
                if agent_or_implementation in ("developer", "executive"):
                    yield agent_or_implementation, message

                else:  # last result
                    # Add the implementation to our list
                    all_implementations.append(agent_or_implementation)
                    summary = message

        final_code = self.dev.integrate_components(components, all_implementations, self.starting_prompt)

        if self.deploy:
            if self.aws is None:
                raise ValueError("Cannot deploy without AWSAgent")
            cast(AWSAgent, self.aws).deploy(final_code, self.uuid)

        self.update(status=ProjectStatus.FINISHED)
        yield "developer", final_code


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
        return current_project.do_work()


async def communicative_dehallucination(
    executive: Executive,
    developer: Developer,
    summary: str,
    component: str,
    max_iter: int = 1,
):
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
    for _ in range(max_iter):
        question = developer.ask_question(context)

        if question == "No Question":
            break

        yield "developer", question
        await asyncio.sleep(0)

        answer = executive.answer_question(context, question)
        q_and_a.append((question, answer))

        yield "executive", answer
        await asyncio.sleep(0)

    if q_and_a:
        context += "\nComponent Clarifications:"
        for question, answer in q_and_a:
            context += f"\nQuestion: {question}"
            context += f"\nAnswer: {answer}"

    # Developer implements component based on clarified context
    implementation = developer.implement_component(context)

    yield "developer", implementation

    await asyncio.sleep(0)
    # Generate a summary of what has been achieved
    summary = executive.generate_summary(summary, implementation)

    yield "executive", summary
    await asyncio.sleep(0)
    yield implementation, summary
    await asyncio.sleep(0)
