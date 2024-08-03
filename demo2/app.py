import uuid

from flask import Flask, render_template, request, session

from concrete import orchestrator

app = Flask(__name__)


def invoke_concrete(input_str: str):
    """
    Returns a valid HTML element
    """
    so = orchestrator.SoftwareOrchestrator()
    element = so.agents["dev"].implement_html_element(input_str)
    return "\n".join(element.strip().split("\n")[1:-1])


@app.route("/", methods=["GET", "POST"])
def index():
    if "user_id" not in session:
        session["user_id"] = str(uuid.uuid4())

    if "previous_elements" not in session:
        session["previous_elements"] = []

    if request.method == "POST":
        input_string = request.form.get("input_name")
        if input_string:
            generated_html = invoke_concrete(input_string)
            session["previous_elements"].append(generated_html)  # Store the new element
            session.modified = True  # Ensure the session is saved

    return render_template(
        "index.html",
        previous_elements=session["previous_elements"],
    )
