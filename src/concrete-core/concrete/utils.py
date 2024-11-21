import base64
import os
from collections import defaultdict, deque
from collections.abc import Callable
from datetime import timedelta
from typing import Any, TypeVar

import dotenv
import jwt

dotenv.load_dotenv(override=True)

# region AI generated
# # These are slow-changing, so the certs are hardcoded directly here
GOOGLE_OIDC_DISCOVERY = "https://accounts.google.com/.well-known/openid-configuration"
# GOOGLE_OIDC_CONFIG = requests.get(GOOGLE_OIDC_DISCOVERY).json()
GOOGLE_OIDC_ALGOS = ["RS256"]
# GOOGLE_JWKS_URI = GOOGLE_OIDC_CONFIG["jwks_uri"]
GOOGLE_JWKS_URI = "https://www.googleapis.com/oauth2/v3/certs"
google_jwks_client = jwt.PyJWKClient(GOOGLE_JWKS_URI)


def verify_jwt(jwt_token: str, access_token: str) -> dict[str, str]:
    """
    Raise an assertion error if the JWT cannot be verified.
    Verifies token authenticity again Google's public keys.
    """
    signing_key = google_jwks_client.get_signing_key_from_jwt(jwt_token)
    data = jwt.PyJWT().decode_complete(
        jwt=jwt_token,
        key=signing_key.key,
        algorithms=GOOGLE_OIDC_ALGOS,
        audience=os.environ["GOOGLE_OAUTH_CLIENT_ID"],
        # Allow two weeks stale tokens
        leeway=timedelta(weeks=2).total_seconds(),
    )
    # For payload details, see
    # https://developers.google.com/identity/openid-connect/openid-connect#an-id-tokens-payload
    payload, header = data["payload"], data["header"]
    alg_obj = jwt.get_algorithm_by_name(header["alg"])
    digest = alg_obj.compute_hash_digest(bytes(access_token, "utf-8"))
    at_hash = base64.urlsafe_b64encode(digest[: (len(digest) // 2)]).rstrip(b"=")
    # Check signature
    assert at_hash == bytes(payload["at_hash"], "utf-8")
    # Simple checks
    # See https://developers.google.com/identity/openid-connect/openid-connect#validatinganidtoken
    assert payload["iss"] in {"https://accounts.google.com", "accounts.google.com"}
    assert payload["aud"] == os.environ["GOOGLE_OAUTH_CLIENT_ID"]
    return payload


def map_python_type_to_json_type(py_type) -> str:
    """
    Maps Python types to JSON schema types.
    """
    type_map = {
        str: "string",
        float: "number",
        bool: "boolean",
        int: "integer",
        dict: "object",
        list: "array",
        # TODO AnyOf and Enum
    }
    if py_type in type_map:
        return type_map[py_type]
    else:
        raise ValueError(f"Unexpected Python type: {py_type}")


# endregion


NodeId = TypeVar("NodeId")
Edge = TypeVar("Edge")


def find_sources_and_sinks(
    nodes: dict[NodeId, Any],
    edges: dict[NodeId, list[Edge]],
    get_neighbor: Callable[[Edge], NodeId] = lambda x: x,  # type: ignore[assignment, return-value]
) -> tuple[list[NodeId], list[NodeId]]:
    in_degree: defaultdict[NodeId, int] = defaultdict(int)
    out_degree: dict[NodeId, int] = {node: len(edges.get(node, [])) for node in nodes}

    for node in nodes:
        # For each node, check its neighbors (outgoing edges)
        neighbors = {get_neighbor(edge) for edge in edges.get(node, [])}
        for neighbor in neighbors:
            in_degree[neighbor] += 1

    source_nodes = [node for node in nodes if in_degree[node] == 0 and out_degree[node] > 0]
    sink_nodes = [node for node in nodes if in_degree[node] > 0 and out_degree[node] == 0]

    return source_nodes, sink_nodes


def bfs_traversal(
    edges: dict[NodeId, list[Edge]],
    start_nodes: list[NodeId],
    end_nodes: list[NodeId] = [],
    process_node: Callable[[NodeId], Any] = print,
    process_edge: Callable[[NodeId, Edge], Any] = print,
    get_neighbor: Callable[[Edge], NodeId] = lambda x: x,  # type: ignore[assignment, return-value]
):
    end_nodes_set = set(end_nodes)

    def bfs(queue: deque[NodeId], visited: set[NodeId]) -> set[NodeId]:
        if not queue:
            return visited  # If queue is empty, return visited nodes (end condition)

        node = queue.popleft()
        if node in visited:
            return bfs(queue, visited)  # Skip if already visited

        # Process the current node
        process_node(node)
        visited = visited | {node}

        # If an end node is reached and provided, stop traversal
        if node in end_nodes_set:
            return visited

        for edge in edges.get(node, []):
            process_edge(node, edge)

        # Enqueue unvisited neighbors
        neighbors = [get_neighbor(edge) for edge in edges.get(node, [])]
        unvisited_neighbors = deque(neighbor for neighbor in neighbors if neighbor not in visited)
        return bfs(queue + unvisited_neighbors, visited)

    return bfs(deque(start_nodes), set())
