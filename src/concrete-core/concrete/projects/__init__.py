from .dag_project import DAGNode, Project
from .software_project import SoftwareProject

PROJECTS: dict[str, Project] = {}

__all__ = ["DAGNode", "Project", "SoftwareProject"]
