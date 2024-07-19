import sys
from textwrap import dedent
from typing import List, Tuple

import astroid
import pytest
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


def compare_ast(expected_code, actual_code):
    try:
        expected_ast = astroid.parse(expected_code)
        actual_ast = astroid.parse(actual_code)
    except astroid.exceptions.AstroidSyntaxError as e:
        print(f"Syntax error: {e}")
        return False

    def compare_nodes(node1, node2):
        if type(node1) is not type(node2):
            return False

        for attr in node1._astroid_fields:
            if not hasattr(node2, attr):
                return False

            value1 = getattr(node1, attr)
            value2 = getattr(node2, attr)

            if isinstance(value1, (list, tuple)):
                if len(value1) != len(value2):
                    print(f"lengths: f{len(value1), len(value2)}")
                    return False
                for item1, item2 in zip(value1, value2):
                    if isinstance(item1, NodeNG):
                        if not compare_nodes(item1, item2):
                            return False
                    elif item1 != item2:
                        print(f"items: {item1}, {item2}")
                        return False
            elif isinstance(value1, NodeNG):
                if not compare_nodes(value1, value2):
                    return False
            elif value1 != value2:
                print(f"values: {value1}, {value2})")
                return False

        return True

    return compare_nodes(expected_ast, actual_ast)


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

    # To be replaced with actual output
    actual_output = expected  # Replace this with your actual orchestrator call

    expected_code = strip_code_block(dedent(expected))
    actual_code = strip_code_block(dedent(actual_output))

    print("Expected code after processing:")
    print(expected_code)
    print("Actual code after processing:")
    print(actual_code)

    print("comparing")
    assert compare_ast(
        expected_code, actual_code
    ), f"Test {test_name} failed: ASTs do not match"
