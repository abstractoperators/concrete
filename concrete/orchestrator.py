import json
from collections import defaultdict
from collections.abc import AsyncGenerator
from textwrap import dedent
from typing import Any, Callable
from uuid import UUID, uuid1, uuid4

from . import prompts
from .clients import Client_con, OpenAIClient
from .models.messages import (
    PlannedComponents,
    ProjectDirectory,
    ProjectFile,
    Summary,
    TextMessage,
    Tool,
)
from .operators import Developer, Executive, Operator
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


class DAGProject(StatefulMixin):
    """
    Represents a DAG of Operator executions.
    Manages DAGNode executions and dependencies.
    """

    def __init__(
        self,
        options: dict = {},
    ) -> None:
        self.edges: dict[DAGNode, list[tuple[DAGNode, str, Callable]]] = defaultdict(list)
        self.options = options

        self.nodes: set[DAGNode] = set()

    def add_edge(
        self,
        child: "DAGNode",
        parent: "DAGNode",
        res_name: str,
        res_transformation: Callable = lambda x: x,
    ) -> None:
        """
        child: Downstream node
        parent: Upstream node
        res_name: Name of the kwarg for the child
        res_mutation: Function to apply to the parent result before passing to the child
        """

        if child not in self.nodes or parent not in self.nodes:
            raise ValueError("Nodes must be added before adding edges")

        self.edges[parent].append((child, res_name, res_transformation))

    def add_node(self, node: "DAGNode") -> None:
        self.nodes.add(node)

    async def execute(self) -> AsyncGenerator[tuple[str, str], None]:
        if not self.is_dag:
            raise ValueError("Graph is not a DAG")
        node_dep_count = {node: 0 for node in self.nodes}
        for edges in self.edges.values():
            for child, _, _ in edges:
                node_dep_count[child] += 1

        no_dep_nodes = set({node for node, deps in node_dep_count.items() if deps == 0})

        while no_dep_nodes:
            ready_node = no_dep_nodes.pop()
            operator_name, res = await ready_node.execute(self.options)

            yield (operator_name, res)

            for child, res_name, res_transformation in self.edges[ready_node]:
                child.update(res_transformation(res), res_name)
                node_dep_count[child] -= 1
                if node_dep_count[child] == 0:
                    no_dep_nodes.add(child)

    @property
    def is_dag(self):
        # AI generated
        visited = set()
        rec_stack = set()

        def dfs(node: DAGNode) -> bool:
            if node not in visited:
                visited.add(node)
                rec_stack.add(node)

                for child, _, _ in self.edges.get(node, []):
                    if child not in visited:
                        if not dfs(child):
                            return False
                    elif child in rec_stack:
                        return False

                rec_stack.remove(node)

            return True

        for node in self.nodes:
            if node not in visited:
                if not dfs(node):
                    return False

        return True


class DAGNode:
    """
    A DAGNode is a configured Operator + str returning callable
    """

    def __init__(
        self,
        task: str,
        operator: Operator,
        default_task_kwargs: dict[str, Any] = {},
        options: dict[str, Any] = {},
    ) -> None:
        """
        task: Name of method on Operator (e.g. 'chat')
        operator: Operator instance
        default_task_kwargs: Default kwargs for the Operator method.
        options: Maps to OperatorOptions. Can also be set in default_task_kwargs as {'options': {...}}
        """
        try:
            self.bound_task = getattr(operator, task)
        except AttributeError:
            raise ValueError(f"{operator} does not have a method {task}")
        self.operator: Operator = operator

        self.task_str = task
        self.dynamic_kwargs: dict[str, Any] = {}
        self.default_task_kwargs = default_task_kwargs  # TODO probably want to manage this in the project
        self.options = options  # Could also throw this into default_task_kwargs

    def update(self, dyn_kwarg_value, dyn_kwarg_name) -> None:
        self.dynamic_kwargs[dyn_kwarg_name] = dyn_kwarg_value

    async def execute(self, options: dict = {}) -> Any:
        """
        options: Optional options ~ OperatorOptions supplementary to instance options
        """
        kwargs = self.default_task_kwargs | self.dynamic_kwargs
        options = self.options | options
        res = self.bound_task(**kwargs, options=self.options | options)
        if options.get('run_async'):
            res = res.get().message

        return type(self.operator).__name__, res

    def __str__(self):
        return f"{type(self.operator).__name__}.{self.task_str}(**{self.default_task_kwargs})"
