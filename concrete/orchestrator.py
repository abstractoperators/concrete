from textwrap import dedent
from typing import Tuple, cast
from uuid import uuid1

from openai.types.beta.thread import Thread

from .agents import Agent, Developer, Executive
from .clients import CLIClient, Client, OpenAIClient
from .context import Context, ProjectState

_HELLO_WORLD_PROMPT = "Create a simple hello world program"


class StatefulMixin:
    def update(self, **kwargs):
        self.context.data.update(kwargs)
        if kwargs.get("state") == ProjectState.FINISHED:
            self.context.data["completed"] = True


class SoftwareProject(StatefulMixin):
    """
    Tracks the execution of a task or objectives
    """

    def __init__(
        self,
        starting_prompt: str,
        orchestrator: "Orchestrator",
        agents: dict[str, Agent],  # codename for agent -> Agent
        clients: dict[str, Client],
        threads: dict[str, Thread] | None = None,  # context -> Thread
    ):
        self.context = Context(self, orchestrator=orchestrator)
        self.uuid = uuid1()  # suffix is unique based on network id
        self.clients = clients
        self.starting_prompt = starting_prompt
        self.agents = agents
        self.threads = threads or {"main": self.clients["openai"].create_thread()}
        self.orchestrator = orchestrator
        self.results = None
        self.update(state=ProjectState.READY)

    def do_work(self) -> str:
        """
        Break down prompt into smaller components and write the code for each individually.
        """
        self.update(state=ProjectState.WORKING, actor=self.agents["exec"])

        orig_components = self.plan()
        components_list = orig_components.split("\n")
        components = [stripped_comp for comp in components_list if (stripped_comp := comp.strip())]
        CLIClient.emit(f"\n[Planned Components]: \n{orig_components}\n")

        summary = ""
        all_implementations = []
        for component in components:
            # Use communicative_dehallucination for each component
            implementation, summary = communicative_dehallucination(
                cast(Executive, self.agents["exec"]),
                cast(Developer, self.agents["dev"]),
                summary,
                component,
                project=self,
                max_iter=1,
            )

            # Add the implementation to our list
            all_implementations.append(implementation)

        final_code = self.agents["dev"].integrate_components(all_implementations, self.starting_prompt)
        self.update(state=ProjectState.FINISHED)
        return final_code

    def plan(self) -> str:
        # TODO: Figure out how to get typehinting for Agents here
        planned_components = self.agents["exec"].plan_components(thread=self.threads["main"])
        return planned_components


class Orchestrator:
    pass


class SoftwareOrchestrator(Orchestrator, StatefulMixin):
    """
    An Orchestrator is a set of configured Agents and a resource manager

    Provides a single entry point for common interactions with agents
    """

    def __init__(self, ws_manager=None):
        self.context = Context(self, orchestrator=self)
        self.update(ws_manager=ws_manager)
        self.uuid = uuid1()
        openai_client = OpenAIClient()
        self.clients = {
            "openai": openai_client,
        }
        self.agents = {
            "exec": Executive(self.clients),
            "dev": Developer(self.clients),
        }
        self.update(state=ProjectState.READY)

    def process_new_project(self, starting_prompt: str):
        self.update(state=ProjectState.WORKING)
        # Immediately spin off a primary thread with the prompt
        threads = {"main": self.clients["openai"].create_thread(starting_prompt)}
        current_project = SoftwareProject(
            starting_prompt=starting_prompt or _HELLO_WORLD_PROMPT,
            agents=self.agents,
            orchestrator=self,
            threads=threads,
            clients=self.clients,
        )
        final_code = current_project.do_work()
        self.update(state=ProjectState.FINISHED)
        return final_code


def communicative_dehallucination(
    executive: Executive,
    developer: Developer,
    summary: str,
    component: str,
    project: SoftwareProject,
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
            - summary (str): A concise summary of what has been achieved for this component.
    """

    context = dedent(
        f"""Previous Components summarized:\n{summary}
    Current Component: {component}"""
    )
    CLIClient.emit(f"Context: \n{context}\n")

    # Iterative Q&A process
    q_and_a = []
    for i in range(max_iter):
        # Developer asks a question
        question = developer.ask_question(context)
        CLIClient.emit(f"Developer's question:\n {question}\n")

        if question == "No Question":
            break

        # Executive answers the question
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
    implementation = developer.implement_component(context)
    CLIClient.emit(implementation)

    # Generate a summary of what has been achieved
    summary = executive.generate_summary(summary, implementation)
    CLIClient.emit(f"Summary: {summary}")

    return implementation, summary
