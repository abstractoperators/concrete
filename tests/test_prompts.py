import difflib
from textwrap import dedent
from typing import List, Tuple

import pytest
from concrete.orchestrators import Orchestrator

# TODO: decide where utils go
# from concrete.utils import remove_comments

test_fixture: List[Tuple[str, str, str]] = [
    (
        "helloworld_flaskapp",
        "Provide the code to quickstart a basic builtin Flask server. The Flask server should only show Hello World",
        """
        ```python
        from flask import Flask
        app = Flask(__name__)
        @app.route('/')
        def hello():
            return 'Hello, World!'
        if __name__ == '__main__':
            app.run(debug=True)
        ```
        """,
    ),
]


def strip_code_block(text):
    """Remove markdown code block syntax if present."""
    lines = text.strip().split("\n")
    if lines[0].strip() == "```python" and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1])
    return text


@pytest.mark.skip(reason="Probabilistic")
@pytest.mark.parametrize("test_name,prompt,expected", test_fixture)
def test_simple_prompts_string_comp(test_name, prompt, expected):
    """
    Iterate over simple prompts and check the output generated against a previous run via string diff.
    Args:
    test_name (str): Name of the project for the ai agent ensemble to complete.
    prompt (str): Initial prompt for the project.
    expected (str): Expected output.
    """
    # TODO Fix this and have it actually run
    actual = Orchestrator.main(prompt)

    # # For developing tester.
    # actual = dedent(
    #     """```python
    # from flask import Flask

    # app = Flask(__name__)

    # @app.route('/')
    # def hello_world():
    #     return 'Hello, World!'

    # if __name__ == '__main__':
    #     app.run()
    # ```"""
    # )

    actual = dedent(strip_code_block(actual))
    # actual = remove_comments(actual)

    expected = dedent(strip_code_block(expected))
    # expected = remove_comments(expected)

    if actual != expected:
        actual = actual.split("\n")
        expected = expected.split("\n")
        with open(f"logs/diff_log_{test_name}.txt", "w") as f:
            for line in difflib.Differ().compare(expected, actual):
                f.write(line + "\n")

    assert actual == expected
