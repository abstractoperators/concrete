from concrete.clients import CLIClient
from concrete.models.messages import Tool
from concrete.tools import TOOLS_REGISTRY, MetaTool


def tool_name_to_class(tool_name: str) -> "MetaTool":
    """
    Returns the class object of a tool given its name.
    """
    return TOOLS_REGISTRY[tool_name]


def invoke_tool(tool: Tool):
    """
    Invokes a tool on a message.
    Throws KeyError if the tool doesn't exist.
    Throws AttributeError if the function on the tool doesn't exist.
    Throws TypeError if the parameters are wrong.
    """
    tool_name = tool.tool_name
    tool_function = tool.tool_method.strip("()")
    if "." in tool_function:
        tool_function = tool_function.split('.')[-1]
    tool_parameters = tool.tool_parameters
    kwargs = {param.name: param.value for param in tool_parameters}
    CLIClient.emit(f"Invoking {tool_name}.{tool_function} with {kwargs}")

    func = getattr(tool_name_to_class(tool_name), tool_function)  # type: ignore

    return func(**kwargs)
