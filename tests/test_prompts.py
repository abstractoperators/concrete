import pytest

from concrete import orchestrator

test_fixture: list[tuple[str, str, str]] = [
   ("helloworld_flaskapp",
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
    """)
]

@pytest.mark.parametrize("actual,expected", [(True, True), (1, 1), ('two', 'three')])
def test_foo(actual, expected):
    assert actual == expected


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
    assert orchestrator.main(prompt) == expected