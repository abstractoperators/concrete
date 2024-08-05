HELLO_WORLD_PROMPT = "Create a simple hello world program"
SELF_MODIFYING_WEBSITE = """
Generate a website using Flask which has an input form at the top.
When the input form is submitted, it should call `invoke_concrete` with the form input.
Include the following function `invoke_concrete` with the server code:
```python
from concrete import orchestrator

def invoke_concrete(input_str: str):
    '''
    Returns a valid html element
    '''
    so = orchestrator.SoftwareOrchestrator()
    element = so.agents['dev'].implement_html_element(input_str)
    return "\n".join(element.strip().split('\n')[1:-1])
```
`invoke_concrete` will return valid html that should be added onto the webpage as list item along with previously generate elements.
Do not make a separate html file, inline it directly with render_template_string.
"""  # noqa:E501
