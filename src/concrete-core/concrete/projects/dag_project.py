from collections import defaultdict
from collections.abc import AsyncGenerator
from typing import Any, Callable

from concrete.mermaid import FlowchartDirection
from concrete.operators import Operator
from concrete.state import StatefulMixin
from concrete.utils import bfs_traversal, find_sources_and_sinks


class Project(StatefulMixin):
    """
    Represents a generic DAG of Operator executions.
    Manages DAGNode executions and dependencies.
    """

    def __init__(
        self,
        options: dict = {},
    ) -> None:
        self.edges: dict[str, list[tuple[str, str, Callable]]] = defaultdict(list)
        self.options = options

        self.nodes: dict[str, DAGNode] = {}

    def add_edge(
        self,
        parent: str,
        child: str,
        res_name: str,
        res_transformation: Callable = lambda x: x,
    ) -> tuple[str, str, str]:
        """
        child: Downstream node
        parent: Upstream node
        res_name: Name of the kwarg for the child
        res_transformation: Function to apply to the parent result before passing to the child
        """

        if child not in self.nodes or parent not in self.nodes:
            raise ValueError("Nodes must be added before adding edges")

        self.edges[parent].append((child, res_name, res_transformation))

        return (parent, child, res_name)

    def add_node(self, node: "DAGNode") -> "DAGNode":
        self.nodes[node.name] = node
        return node

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
            operator_name, res = await self.nodes[ready_node].execute(self.options)

            yield (operator_name, res)

            for child, res_name, res_transformation in self.edges[ready_node]:
                self.nodes[child].update(res_name, res_transformation(res))
                node_dep_count[child] -= 1
                if node_dep_count[child] == 0:
                    no_dep_nodes.add(child)

    def draw_mermaid(
        self,
        title: str | None = None,
        direction: FlowchartDirection = FlowchartDirection.TOP_DOWN,
        start_nodes: list[str] = [],
        end_nodes: list[str] = [],
    ) -> str:
        """Draws a Mermaid flowchart from the DAG.

        Args:
            title (str, optional): Title of the flowchart. Defaults to None.
            direction (FlowchartDirection, optional):
                Direction of the flowchart, i.e. start and end positions. Defaults to top down.
            start_nodes (list[str], optional): Names of the source (i.e. start) nodes. Defaults to project source nodes.
            end_nodes (list[str], optional): Names of the sink (i.e. end) nodes. Defaults to project sink nodes.

        Returns:
            str: Mermaid flowchart syntax.
        """
        flowchart = f"flowchart {direction}\n"

        if title is not None:
            flowchart = flowchart + f"---\ntitle: {title}\n---\n"

        remove_whitespace: Callable[[str], str] = lambda string: "".join(string.split())
        get_child: Callable[[tuple[str, str, Callable]], str] = lambda edge: edge[0]

        def process_node(node: str) -> None:
            nonlocal flowchart
            flowchart = flowchart + f"\t{remove_whitespace(node)}([\"{self.nodes[node]!s}\"])\n"

        def process_edge(node: str, edge: tuple[str, str, Callable]) -> None:
            # TODO: design a good string representation for result transformation
            nonlocal flowchart
            flowchart = flowchart + f"\t{remove_whitespace(node)} -->|{edge[1]}| {remove_whitespace(edge[0])}\n"

        if not start_nodes or not end_nodes:
            sources, sinks = find_sources_and_sinks(self.nodes, self.edges, get_child)
            if not start_nodes:
                start_nodes = sources
            if not end_nodes:
                end_nodes = sinks

        bfs_traversal(
            self.edges,
            start_nodes,
            end_nodes,
            process_node=process_node,
            process_edge=process_edge,
            get_neighbor=get_child,
        )

        return flowchart

    @property
    def is_dag(self) -> bool:
        # AI generated
        visited: set[str] = set()
        rec_stack: set[str] = set()

        def dfs(node: str) -> bool:
            if node not in visited:
                visited.add(node)
                rec_stack.add(node)

                for child, _, _ in self.edges[node]:
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
        name: str,
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

        self.name = name
        self.boost_str = task
        self.dynamic_kwargs: dict[str, Any] = {}
        self.default_task_kwargs = default_task_kwargs  # TODO probably want to manage this in the project
        self.options = options  # Could also throw this into default_task_kwargs

    def update(self, dyn_kwarg_name, dyn_kwarg_value) -> None:
        self.dynamic_kwargs[dyn_kwarg_name] = dyn_kwarg_value

    async def execute(self, options: dict = {}) -> Any:
        """
        options: Optional options ~ OperatorOptions supplementary to instance options
        """
        kwargs = self.default_task_kwargs | self.dynamic_kwargs
        options = self.options | options
        print(kwargs)
        res = self.bound_task(**kwargs, options=self.options | options)
        if options.get("run_async"):
            res = res.get().message

        return self.name, res

    def __str__(self):
        return f"{type(self.operator).__name__}.{self.boost_str}(**{self.default_task_kwargs})"
