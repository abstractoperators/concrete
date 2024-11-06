# type: ignore
# TODO: Remove above

import fnmatch
import os
from queue import Queue
from uuid import UUID

try:
    from concrete_db import crud
    from concrete_db.orm import Session, models
except ImportError:
    raise ImportError("Install concrete_db to use knowledge tools")

from concrete.clients import CLIClient, OpenAIClient
from concrete.models.messages import ChildNodeSummary, NodeSummary
from concrete.tools import MetaTool


class KnowledgeGraphTool(metaclass=MetaTool):
    """
    Converts a repository into a knowledge graph.
    """

    @classmethod
    def _parse_to_tree(
        cls,
        org: str,
        repo: str,
        branch: str,
        dir_path: str,
        rel_gitignore_path: str | None = None,
    ) -> UUID:
        """
        Converts a directory into an unpopulated knowledge graph.
        Stored in reponode table. Recursive programming is pain -> use a queue.

        args
            dir_path: The path to the directory to convert.
            rel_gitignore_path: Path to .gitignore file relative to root directory.
            branch: git branch of the directory state
            sha: sha of the directory state
        Returns
            UUID: The root node id of the knowledge graph.
        """
        to_split: Queue[UUID] = Queue()

        if (root_node_id := KnowledgeGraphTool._get_node_by_path(org, repo, branch)) is None:
            root_node = models.RepoNodeCreate(
                org=org,
                repo=repo,
                partition_type="directory",
                name=f"org/{repo}",
                summary="",
                children_summaries="",
                abs_path=dir_path,
                branch=branch,
            )

            with Session() as db:
                root_node_id = crud.create_repo_node(db=db, repo_node_create=root_node).id
                to_split.put(root_node_id)

            ignore_paths = [".git", ".venv", ".github", "poetry.lock", "*.pdf"]
            if rel_gitignore_path:
                with open(os.path.join(dir_path, rel_gitignore_path), "r") as f:
                    gitignore = f.readlines()
                    gitignore = [path.strip() for path in gitignore if path.strip() and not path.startswith("#")]
                    ignore_paths.extend(gitignore)

            while len(to_split.queue) > 0:
                children_ids = KnowledgeGraphTool._split_and_create_nodes(to_split.get(), ignore_paths)
                for child_id in children_ids:
                    to_split.put(child_id)
                CLIClient.emit(f"Remaining: {to_split.qsize()}")

            KnowledgeGraphTool._upsert_all_summaries_from_leaves(root_node_id)

        return root_node_id

    @classmethod
    def _split_and_create_nodes(cls, parent_id: UUID, ignore_paths) -> list[UUID]:
        """
        Chunks a node into smaller nodes.
        Adds children nodes to database, and returns them for further chunking.
        """
        with Session() as db:
            parent = crud.get_repo_node(db=db, repo_node_id=parent_id)
            if parent is None:
                return []

        children: list[models.RepoNodeCreate] = []
        if parent.partition_type == "directory":
            files_and_directories = os.listdir(parent.abs_path)
            files_and_directories = [
                f for f in files_and_directories if not KnowledgeGraphTool._should_ignore(f, ignore_paths)
            ]
            for file_or_dir in files_and_directories:
                path = os.path.join(parent.abs_path, file_or_dir)

                partition_type = "directory" if os.path.isdir(path) else "file"
                CLIClient.emit(f"Creating {partition_type} {file_or_dir}")
                child = models.RepoNodeCreate(
                    org=parent.org,
                    repo=parent.repo,
                    partition_type=partition_type,
                    name=file_or_dir,
                    summary="",
                    children_summaries="",
                    abs_path=path,
                    parent_id=parent.id,
                    branch=parent.branch,
                )
                children.append(child)

        elif parent.partition_type == "file":
            pass
            # Can possibly create child nodes for functions/classes in the file

        res = []
        for child in children:
            with Session() as db:
                child_node = crud.create_repo_node(db=db, repo_node_create=child)
            res.append(child_node.id)

        return res

    @classmethod
    def _should_ignore(cls, name: str, ignore_patterns: str) -> bool:
        """
        Helper function for deciding whether a file/dir should be in the knowledge graph.
        """
        for pattern in ignore_patterns:
            if pattern.endswith("/"):
                # Directory pattern
                if fnmatch.fnmatch(name + "/", pattern):
                    CLIClient.emit(f"Ignoring directory {name} due to pattern {pattern}")
                    return True
            else:
                # File pattern
                if fnmatch.fnmatch(name, pattern):
                    CLIClient.emit(f"Ignoring file {name} due to pattern {pattern}")
                    return True

        return False

    @classmethod
    def _plot(cls, root_node_id: UUID):
        """
        Plots a knowledge graph node into a graph using Graphviz's 'dot' layout.
        Useful for debugging & testing.
        """
        import matplotlib.pyplot as plt
        import networkx as nx

        G = nx.DiGraph()
        nodes: Queue[UUID] = Queue()
        nodes.put(root_node_id)

        while not nodes.empty():
            node_id = nodes.get()
            with Session() as db:
                node = crud.get_repo_node(db=db, repo_node_id=node_id)
                if node is None:
                    continue
                parent, children = node, node.children

            for child in children:
                G.add_node(child.abs_path)
                G.add_edge(parent.abs_path, child.abs_path)
                nodes.put(child.id)

        def _hierarchy_pos(G, root, levels=None, width=1.0, height=1.0):
            # https://stackoverflow.com/questions/29586520/can-one-get-hierarchical-graphs-from-networkx-with-python-3/29597209#29597209
            """If there is a cycle that is reachable from root, then this will see infinite recursion.
            G: the graph
            root: the root node
            levels: a dictionary
                    key: level number (starting from 0)
                    value: number of nodes in this level
            width: horizontal space allocated for drawing
            height: vertical space allocated for drawing"""
            TOTAL = "total"
            CURRENT = "current"

            def make_levels(levels, node=root, currentLevel=0, parent=None):
                """Compute the number of nodes for each level"""
                if currentLevel not in levels:
                    levels[currentLevel] = {TOTAL: 0, CURRENT: 0}
                levels[currentLevel][TOTAL] += 1
                neighbors = G.neighbors(node)
                for neighbor in neighbors:
                    if not neighbor == parent:
                        levels = make_levels(levels, neighbor, currentLevel + 1, node)
                return levels

            def make_pos(pos, node=root, currentLevel=0, parent=None, vert_loc=0):
                dx = 1 / levels[currentLevel][TOTAL]
                left = dx / 2
                pos[node] = (
                    (left + dx * levels[currentLevel][CURRENT]) * width,
                    vert_loc,
                )
                levels[currentLevel][CURRENT] += 1
                neighbors = G.neighbors(node)
                for neighbor in neighbors:
                    if not neighbor == parent:
                        pos = make_pos(pos, neighbor, currentLevel + 1, node, vert_loc - vert_gap)
                return pos

            if levels is None:
                levels = make_levels({})
            else:
                levels = {level: {TOTAL: levels[level], CURRENT: 0} for level in levels}
            vert_gap = height / (max([level for level in levels]) + 1)
            return make_pos({})

        with Session() as db:
            root_node = crud.get_repo_node(db=db, repo_node_id=root_node_id)
            if not root_node:
                db.close()
                return
        graph_root_node = root_node.abs_path
        pos = _hierarchy_pos(G, root=graph_root_node)

        plt.figure(figsize=(50, 10))
        nx.draw(
            G,
            pos,
            with_labels=True,
            node_color="lightblue",
            node_size=5000,
            arrows=True,
            font_size=6,
            edge_color="gray",
        )

        plt.axis("off")
        plt.show()

    @classmethod
    def _upsert_all_summaries_from_leaves(cls, root_node_id: UUID):
        """
        Creates or overwrites all summaries in the knowledge graph.
        Prerequisite on the graph being built.
        """
        node_ids: list[list[UUID]] = [[root_node_id]]  # Stack of node ids in ascending order of depth. root -> leaf
        with Session() as db:
            while node_ids[-1] != []:
                to_append = []
                for node_id in node_ids[-1]:
                    node = crud.get_repo_node(db=db, repo_node_id=node_id)
                    if node is not None:
                        children = node.children
                        children_ids = [child.id for child in children]
                        to_append.extend(children_ids)
                node_ids.append(to_append)

            while node_ids:
                for node_id in node_ids.pop():
                    node = crud.get_repo_node(db=db, repo_node_id=node_id)
                    if node is not None:
                        if node.partition_type == "directory":
                            KnowledgeGraphTool._upsert_parent_summary_from_children(node_id)
                        elif node.partition_type == "file":
                            KnowledgeGraphTool._upsert_leaf_summary(node_id)

    @classmethod
    def _upsert_parent_summaries_to_root(cls, child_id: UUID) -> None:
        """
        Recursively updates all parent summaries up until the root. Prerequisite on the graph being built.
        """
        with Session() as db:
            child = crud.get_repo_node(db=db, repo_node_id=child_id)
            if child is not None:
                parent_id = child.parent_id
                if parent_id is not None:
                    KnowledgeGraphTool._upsert_parent_summary_from_child(child_id)

        if child is not None and child.parent_id is not None:
            KnowledgeGraphTool._upsert_parent_summaries_to_root(child.parent_id)

    @classmethod
    def _upsert_parent_summary_from_child(cls, child_node_id: UUID):
        """
        Updates parent summary with child summary.
        """
        from concrete_core.operators import Executive

        with Session() as db:
            child = crud.get_repo_node(db=db, repo_node_id=child_node_id)
            if child and child.parent_id:
                parent = crud.get_repo_node(db=db, repo_node_id=child.parent_id)

            if not child or not parent:
                return

            parent_id = parent.id
            parent_summary = parent.summary
            parent_children_summaries = parent.children_summaries
            child_summary = child.summary
            child_abs_path = child.abs_path

        exec = Executive(clients={"openai": OpenAIClient()})
        node_summary: NodeSummary = exec.update_parent_summary(
            parent_summary=parent_summary,
            child_summary=child_summary,
            parent_child_summaries=parent_children_summaries,
            child_name=child_abs_path,
            message_format=NodeSummary,
        )  # type: ignore

        with Session() as db:
            parent = crud.get_repo_node(db=db, repo_node_id=parent_id)
            if parent is not None:
                parent_overall_summary = node_summary.overall_summary
                parent_children_summaries = "\n".join(
                    [
                        f"{child_summary.node_name}: {child_summary.summary}"
                        for child_summary in node_summary.children_summaries
                    ]
                )
                parent_node_update = models.RepoNodeUpdate(
                    summary=parent_overall_summary,
                    children_summaries=parent_children_summaries,
                )
                crud.update_repo_node(db=db, repo_node_id=parent_id, repo_node_update=parent_node_update)

    @classmethod
    def _upsert_leaf_summary(cls, leaf_node_id: UUID):
        """
        Creates or overwrites a leaf summary.
        TODO: Current implementation assumes that the leaf is a file - so generated summary is based on file contents.
        Eventually, this should be able to summarize functions/classes in a file.
        """
        import chardet
        from concrete_core.operators import Executive

        with Session() as db:
            leaf_node = crud.get_repo_node(db=db, repo_node_id=leaf_node_id)
            if leaf_node is not None and leaf_node.abs_path is not None and leaf_node.partition_type == "file":
                path = leaf_node.abs_path

        with open(path, "rb") as file:
            raw_data = file.read()
        result = chardet.detect(raw_data)
        encoding = result["encoding"]

        try:
            if encoding is None:
                encoding = "utf-8"
            contents = raw_data.decode(encoding)
        except UnicodeDecodeError:
            contents = raw_data.decode("utf-8", errors="replace")

        exec = Executive(clients={"openai": OpenAIClient()})
        child_node_summary = exec.summarize_file(
            contents=contents,
            file_name=path,
            options={"message_format": ChildNodeSummary},
        )
        repo_node_create = models.RepoNodeUpdate(summary=child_node_summary.summary)
        with Session() as db:
            crud.update_repo_node(db=db, repo_node_id=leaf_node_id, repo_node_update=repo_node_create)

    @classmethod
    def _upsert_parent_summary_from_children(cls, repo_node_id: UUID):
        """
        Creates or overwrites a nodes summary using all of its children.
        """
        from concrete_core.operators import Executive

        with Session() as db:
            parent = crud.get_repo_node(db=db, repo_node_id=repo_node_id)
            if parent is None:
                raise ValueError(f"Node {repo_node_id} not found.")

            children = parent.children
            children_ids = [child.id for child in children]
            children_summaries: list[str] = []
            parent_name = parent.abs_path
            for child_id in children_ids:
                child = crud.get_repo_node(db=db, repo_node_id=child_id)
                if child is not None:
                    children_summaries.append(f"{child.abs_path}: {child.summary}")

        exec = Executive({"openai": OpenAIClient()})
        node_summary = exec.summarize_from_children(
            children_summaries, parent_name, options={"message_format": NodeSummary}
        )
        overall_summary = node_summary.overall_summary
        parent_children_summaries = "\n".join(
            [f"{child_summary.node_name}: {child_summary.summary}" for child_summary in node_summary.children_summaries]
        )
        parent_node_update = models.RepoNodeUpdate(
            summary=overall_summary, children_summaries=parent_children_summaries
        )
        with Session() as db:
            crud.update_repo_node(db=db, repo_node_id=repo_node_id, repo_node_update=parent_node_update)

    @classmethod
    def get_node_summary(cls, node_id: UUID) -> tuple[str, str]:
        """
        Returns the summary of a node.
        (overall_summary, children_summaries)
        """
        with Session() as db:
            node = crud.get_repo_node(db=db, repo_node_id=node_id)
            if node is None:
                return ("", "")
            return (node.summary, node.children_summaries)

    @classmethod
    def get_node_parent(cls, node_id: UUID) -> UUID | None:
        """
        Returns the UUID of the parent of node (if it exists, else None).
        """
        with Session() as db:
            node = crud.get_repo_node(db=db, repo_node_id=node_id)
            if node is None or node.parent_id is None:
                return None
            return node.parent_id

    @classmethod
    def get_node_children(cls, node_id: UUID) -> dict[str, UUID]:
        """
        Returns the UUIDs of the children of a node.
        {child_name: child_id}
        """
        with Session() as db:
            node = crud.get_repo_node(db=db, repo_node_id=node_id)
            if node is None:
                return {}
            children = node.children
            return {child.name: child.id for child in children}

    @classmethod
    def get_node_path(cls, node_id: UUID) -> str:
        """
        Returns the abs_path attribute of a node.
        """
        with Session() as db:
            node = crud.get_repo_node(db=db, repo_node_id=node_id)
            if node is None:
                return ""
            return node.abs_path

    @classmethod
    def _get_node_by_path(cls, org: str, repo: str, branch: str, path: str | None = None) -> UUID | None:
        """
        Returns the UUID of a node by its path. Enables file pointer lookup.
        If path is none, returns the root node
        """
        with Session() as db:
            if path is None:
                node = crud.get_root_repo_node(db=db, org=org, repo=repo, branch=branch)
            else:
                node = crud.get_repo_node_by_path(db=db, org=org, repo=repo, abs_path=path, branch=branch)
            if node is None:
                return None
            return node.id
