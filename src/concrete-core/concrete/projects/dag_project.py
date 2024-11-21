from collections import defaultdict
from collections.abc import AsyncGenerator
from typing import Any, Callable

from concrete.operators import Operator
from concrete.state import StatefulMixin


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
        first_node: str | None = None,
        last_node: str | None = None,
        with_styles: bool = True,
        curve_style: "CurveStyle" = None,
        node_styles: "NodeStyles" = None,
        wrap_label_n_words: int = 9,
    ) -> str:
        """Draws a Mermaid graph using the provided graph data.
        Adapted from langchain_core.runnables.graph_mermaid.draw_mermaid

        Args:
            first_node (str, optional): Id of the first node. Defaults to None.
            last_node (str, optional): Id of the last node. Defaults to None.
            with_styles (bool, optional): Whether to include styles in the graph.
                Defaults to True.
            curve_style (CurveStyle, optional): Curve style for the edges.
                Defaults to CurveStyle.LINEAR.
            node_styles (NodeStyles, optional): Node colors for different types.
                Defaults to NodeStyles().
            wrap_label_n_words (int, optional): Words to wrap the edge labels.
                Defaults to 9.

        Returns:
            str: Mermaid graph syntax.
        """
        pass
        # Initialize Mermaid graph configuration
        mermaid_graph = (
            (
                f"%%{{init: {{'flowchart': {{'curve': '{curve_style.value}'"
                f"}}}}}}%%\ngraph TD;\n"
            )
            if with_styles
            else "graph TD;\n"
        )

        if with_styles:
            # Node formatting templates
            default_class_label = "default"
            format_dict = {default_class_label: "{0}({1})"}
            if first_node is not None:
                format_dict[first_node] = "{0}([{1}]):::first"
            if last_node is not None:
                format_dict[last_node] = "{0}([{1}]):::last"

            # Add nodes to the graph
            for key, node in nodes.items():
                node_name = node.name.split(":")[-1]
                label = (
                    f"<p>{node_name}</p>"
                    if node_name.startswith(tuple(MARKDOWN_SPECIAL_CHARS))
                    and node_name.endswith(tuple(MARKDOWN_SPECIAL_CHARS))
                    else node_name
                )
                if node.metadata:
                    label = (
                        f"{label}<hr/><small><em>"
                        + "\n".join(
                            f"{key} = {value}" for key, value in node.metadata.items()
                        )
                        + "</em></small>"
                    )
                node_label = format_dict.get(key, format_dict[default_class_label]).format(
                    _escape_node_label(key), label
                )
                mermaid_graph += f"\t{node_label}\n"

        # Group edges by their common prefixes
        edge_groups: dict[str, list[Edge]] = {}
        for edge in edges:
            src_parts = edge.source.split(":")
            tgt_parts = edge.target.split(":")
            common_prefix = ":".join(
                src for src, tgt in zip(src_parts, tgt_parts) if src == tgt
            )
            edge_groups.setdefault(common_prefix, []).append(edge)

        seen_subgraphs = set()

        def add_subgraph(edges: list[Edge], prefix: str) -> None:
            nonlocal mermaid_graph
            self_loop = len(edges) == 1 and edges[0].source == edges[0].target
            if prefix and not self_loop:
                subgraph = prefix.split(":")[-1]
                if subgraph in seen_subgraphs:
                    msg = (
                        f"Found duplicate subgraph '{subgraph}' -- this likely means that "
                        "you're reusing a subgraph node with the same name. "
                        "Please adjust your graph to have subgraph nodes with unique names."
                    )
                    raise ValueError(msg)

                seen_subgraphs.add(subgraph)
                mermaid_graph += f"\tsubgraph {subgraph}\n"

            for edge in edges:
                source, target = edge.source, edge.target

                # Add BR every wrap_label_n_words words
                if edge.data is not None:
                    edge_data = edge.data
                    words = str(edge_data).split()  # Split the string into words
                    # Group words into chunks of wrap_label_n_words size
                    if len(words) > wrap_label_n_words:
                        edge_data = "&nbsp<br>&nbsp".join(
                            " ".join(words[i : i + wrap_label_n_words])
                            for i in range(0, len(words), wrap_label_n_words)
                        )
                    if edge.conditional:
                        edge_label = f" -. &nbsp;{edge_data}&nbsp; .-> "
                    else:
                        edge_label = f" -- &nbsp;{edge_data}&nbsp; --> "
                else:
                    edge_label = " -.-> " if edge.conditional else " --> "

                mermaid_graph += (
                    f"\t{_escape_node_label(source)}{edge_label}"
                    f"{_escape_node_label(target)};\n"
                )

            # Recursively add nested subgraphs
            for nested_prefix in edge_groups:
                if not nested_prefix.startswith(prefix + ":") or nested_prefix == prefix:
                    continue
                add_subgraph(edge_groups[nested_prefix], nested_prefix)

            if prefix and not self_loop:
                mermaid_graph += "\tend\n"

        # Start with the top-level edges (no common prefix)
        add_subgraph(edge_groups.get("", []), "")

        # Add remaining subgraphs
        for prefix in edge_groups:
            if ":" in prefix or prefix == "":
                continue
            add_subgraph(edge_groups[prefix], prefix)

        # Add custom styles for nodes
        if with_styles:
            mermaid_graph += _generate_mermaid_graph_styles(node_styles or NodeStyles())
        return mermaid_graph


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
