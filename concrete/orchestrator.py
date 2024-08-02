import os
import time
from multiprocessing import Pool, pool
from multiprocessing.pool import AsyncResult
from textwrap import dedent
from typing import Tuple
from uuid import UUID, uuid1

import django
from django.db import transaction
from openai.types.beta.thread import Thread

from .agents import Developer, Executive
from .clients import CLIClient, Client, OpenAIClient
from .state import ProjectStatus, State

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "concrete.settings")
django.setup()

from .models import Message, MessageStatus, MessageType  # noqa:E402

_HELLO_WORLD_PROMPT = "Create a simple hello world program"


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
        orchestrator: UUID,
        exec: Executive,
        dev: Developer,
        clients: dict[str, Client],
        threads: dict[str, Thread] | None = None,  # context -> Thread
    ):
        self.state = State(self, orchestrator=orchestrator)
        self.clients = clients
        self.starting_prompt = starting_prompt
        self.exec = exec
        self.dev = dev
        self.threads = threads or {"main": self.clients["openai"].create_thread()}
        self.results = None
        self.update(status=ProjectStatus.READY)

    def do_work(self) -> str:
        """
        Break down prompt into smaller components and write the code for each individually.
        """
        self.update(status=ProjectStatus.WORKING, actor=self.exec, target=self.dev)

        orig_components = self.plan()
        components_list = orig_components.split("\n")
        components = [stripped_comp for comp in components_list if (stripped_comp := comp.strip())]
        CLIClient.emit(f"\n[Planned Components]: \n{orig_components}\n")

        summary = ""
        all_implementations = []
        for component in components:
            # Use communicative_dehallucination for each component
            implementation, summary = communicative_dehallucination(
                self.exec,
                self.dev,
                summary,
                component,
                max_iter=1,
            )

            # Add the implementation to our list
            all_implementations.append(implementation)

        final_code = self.dev.integrate_components(all_implementations, self.starting_prompt)
        self.update(status=ProjectStatus.FINISHED)
        return final_code

    def plan(self) -> str:
        # TODO: Figure out how to get typehinting for Agents here
        planned_components = self.exec.plan_components(thread=self.threads["main"])
        return planned_components


class ProjectWorker:
    pass


class SoftwareProjectWorker(ProjectWorker):
    """
    Completes projects that it pulls from message queue
    """

    def __init__(self) -> None:
        openai_client = OpenAIClient()
        self.clients: dict[str, Client] = {
            "openai": openai_client,
        }
        self.exec = Executive(self.clients)
        self.dev = Developer(self.clients)

    def create_project(self, starting_prompt: str, orchestrator_id: UUID) -> SoftwareProject:
        # self.update(status=ProjectStatus.WORKING)
        # Immediately spin off a primary thread with the prompt
        threads = {"main": self.clients["openai"].create_thread(starting_prompt)}
        return SoftwareProject(
            starting_prompt=starting_prompt or _HELLO_WORLD_PROMPT,
            exec=self.exec,
            dev=self.dev,
            orchestrator=orchestrator_id,
            threads=threads,
            clients=self.clients,
        )

    # TODO: Not a proper transaction; if SoftwareProjectWorker fails while processing there is no rollback
    @transaction.atomic
    def query_message_queue(self) -> Message | None:
        messages = Message.objects.filter(message_type=MessageType.COMMAND, message_status=MessageStatus.UNPROCESSED)
        if len(messages) == 0:
            return None
        message = messages[0]
        message.message_status = MessageStatus.PROCESSING
        message.save()
        return message

    def run(self) -> Message:
        message = self.query_message_queue()
        if message:
            software_project = self.create_project(message.prompt, message.orchestrator)
            code = software_project.do_work()
            message.message_status = MessageStatus.PROCESSED
            message.result = code
            message.save()
        return message

    @staticmethod
    def loop(worker_timeout: float = 1) -> None:
        worker = SoftwareProjectWorker()
        while True:
            worker.run()
            time.sleep(worker_timeout)

    @staticmethod
    def multi_loop(num_workers: int = 3, worker_timeout: float = 1) -> tuple[pool.Pool, list[AsyncResult]]:
        pool = Pool(num_workers)
        loop_handles = [
            pool.apply_async(
                SoftwareProjectWorker.loop,
                kwds={'worker_timeout': worker_timeout},
            )
            for _ in range(num_workers)
        ]
        return pool, loop_handles


class Orchestrator:
    pass


class SoftwareOrchestrator(Orchestrator, StatefulMixin):
    """
    An Orchestrator is a set of configured Agents and a resource manager

    Provides a single entry point for common interactions with agents
    """

    def __init__(self) -> None:
        self.uuid = uuid1()

    def run_prompt(self, starting_prompt: str) -> str:
        msg = Message(
            orchestrator=self.uuid,
            message_type=MessageType.COMMAND,
            prompt=starting_prompt,
        )
        msg.save()

        result = None
        while not result:
            responses = (
                Message.objects.filter(orchestrator=self.uuid)
                .filter(message_status=MessageStatus.PROCESSED)
                .filter(prompt=starting_prompt)
                .filter(created_at=msg.created_at)
            )
            for response in responses:
                result = response.result
                break
            time.sleep(1)

        return result


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
    CLIClient.emit(f"Context: \n{context}\n")

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
    implementation = developer.implement_component(context)
    CLIClient.emit(f"Component Implementation:\n{implementation}")

    # Generate a summary of what has been achieved
    summary = executive.generate_summary(summary, implementation)
    CLIClient.emit(f"Summary: {summary}")

    return implementation, summary
