import sys
from textwrap import dedent
from typing import List, Tuple

import astroid
import pytest
from astroid.exceptions import InferenceError
from astroid.nodes import NodeNG

sys.path.append("../")
sys.path.append("../concrete")
from concrete import assistants, orchestrator


def strip_code_block(text):
    """Remove markdown code block syntax if present."""
    lines = text.strip().split("\n")
    if lines[0].strip() == "```python" and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1])
    return text


def remove_comments(text):
    pass


def evaluate_simple_return(node):
    if isinstance(node, astroid.Return):
        if isinstance(node.value, astroid.Const):
            return node.value.value
    return None


def compare_nodes_recursive(node1, node2):
    if type(node1) is not type(node2):
        return False

    if isinstance(
        node1,
        (
            astroid.For,
            astroid.If,
            astroid.BinOp,
            astroid.ListComp,
            astroid.ClassDef,
            astroid.Return,
        ),
    ):
        return compare_nodes(node1, node2)

    try:
        inferred1 = list(node1.infer())
        inferred2 = list(node2.infer())
        if len(inferred1) != len(inferred2):
            return False
        for inf1, inf2 in zip(inferred1, inferred2):
            if type(inf1) is not type(inf2):
                return False
            if hasattr(inf1, "name") and hasattr(inf2, "name"):
                if inf1.name != inf2.name:
                    return False
            if hasattr(inf1, "value") and hasattr(inf2, "value"):
                if inf1.value != inf2.value:
                    return False
            # Recursively compare inferred nodes
            if isinstance(inf1, NodeNG) and isinstance(inf2, NodeNG):
                if not compare_nodes_recursive(inf1, inf2):
                    return False
    except InferenceError:
        pass  # Fall through to attribute comparison

    # Always perform attribute comparison
    for attr in node1._astroid_fields:
        if not hasattr(node2, attr):
            return False
        value1 = getattr(node1, attr)
        value2 = getattr(node2, attr)
        if isinstance(value1, (list, tuple)):
            if len(value1) != len(value2):
                return False
            for item1, item2 in zip(value1, value2):
                if isinstance(item1, NodeNG):
                    if not compare_nodes_recursive(item1, item2):
                        return False
                elif item1 != item2:
                    return False
        elif isinstance(value1, NodeNG):
            if not compare_nodes_recursive(value1, value2):
                return False
        elif value1 != value2:
            return False

    return True


def compare_nodes(node1, node2):
    if isinstance(node1, astroid.For):
        return (
            compare_nodes_recursive(node1.target, node2.target)
            and compare_nodes_recursive(node1.iter, node2.iter)
            and all(
                compare_nodes_recursive(b1, b2)
                for b1, b2 in zip(node1.body, node2.body)
            )
        )
    elif isinstance(node1, astroid.If):
        return (
            compare_nodes_recursive(node1.test, node2.test)
            and all(
                compare_nodes_recursive(b1, b2)
                for b1, b2 in zip(node1.body, node2.body)
            )
            and all(
                compare_nodes_recursive(b1, b2)
                for b1, b2 in zip(node1.orelse, node2.orelse)
            )
        )
    elif isinstance(node1, astroid.BinOp):
        return (
            node1.op == node2.op
            and compare_nodes_recursive(node1.left, node2.left)
            and compare_nodes_recursive(node1.right, node2.right)
        )
    elif isinstance(node1, astroid.ListComp):
        return compare_nodes_recursive(node1.elt, node2.elt) and all(
            compare_nodes_recursive(g1, g2)
            for g1, g2 in zip(node1.generators, node2.generators)
        )
    elif isinstance(node1, astroid.ClassDef):
        return (
            node1.name == node2.name
            and all(
                compare_nodes_recursive(b1, b2)
                for b1, b2 in zip(node1.body, node2.body)
            )
            and all(
                compare_nodes_recursive(b1, b2)
                for b1, b2 in zip(node1.bases, node2.bases)
            )
        )
    elif isinstance(node1, astroid.Return):
        return compare_nodes_recursive(node1.value, node2.value)
    else:
        return False


def compare_ast(expected_code, actual_code):
    try:
        expected_ast = astroid.parse(expected_code)
        actual_ast = astroid.parse(actual_code)
    except astroid.exceptions.AstroidSyntaxError as e:
        print(f"Syntax error: {e}")
        return False

    return compare_nodes_recursive(expected_ast, actual_ast)


test_fixture: List[Tuple[str, str, str]] = [
    (
        "helloworld_flaskapp",
        "Provide the code to quickstart a basic builtin Flask server. The Flask server should only show Hello World",
        """
        ```python
        from flask import Flask
        app = Flask(__name__)
        @app.route('/')
        def hello_world():
            return 'Hello, World!'
        if __name__ == '__main__':
            app.run()
        ```
        """,
    )
]


@pytest.mark.parametrize("test_name,prompt,expected", test_fixture)
def test_simple_prompts(test_name: str, prompt: str, expected: str):
    """
    Iterate over simple prompts and check the output generated against a previous run.
    Args:
    test_name (str): Name of the project for the ai agent ensemble to complete.
    prompt (str): Initial prompt for the project.
    expected (str): Expected output.
    """
    print("Working on test", test_name)

    # To be replaced with actual output # Replaced hello_world() function with hello()
    actual_code = """```python
        from flask import Flask
        
        app = Flask(__name__)
        @app.route('/')
        def hello():
            return 'Hello, Worlddd!'
        if __name__ == '__main__':
            app.run()
            ```
        """

    expected_code = strip_code_block(dedent(expected))
    actual_code = strip_code_block(dedent(actual_code))

    print("\nExpected code after processing:")
    print(expected_code)
    print("\nActual code after processing:")
    print(actual_code)

    print("comparing")
    assert compare_ast(
        expected_code, actual_code
    ), f"Test {test_name} failed: ASTs do not match"

    # actual_code = orchestrator.main(prompt)
    # actual_code = strip_code_block(dedent(actual_code))

    # print("\nExpected code after processing:")
    # print(expected_code)
    # print("\nActual code after processing:")
    # print(actual_code)

    # assert compare_ast(
    #     expected_code, actual_code
    # ), f"Test {test_name} failed: ASTS do not match"
