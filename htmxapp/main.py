from fasthtml import common as f

app, rt = f.fast_app(
    pico=False,
    hdrs=(
        f.Link(rel="preconnect", href="https://fonts.googleapis.com"),
        f.Link(rel="preconnect", href="https://fonts.gstatic.com", crossorigin=""),
        f.Link(
            rel="stylesheet",
            href="https://fonts.googleapis.com/css2?family=Kantumruy+Pro:ital,wght@0,100..700;1,100..700&display=swap",
        ),
        f.Link(
            rel="stylesheet",
            href="https://fonts.googleapis.com/css2?family=Judson:ital,wght@0,400;0,700;1,400&display=swap",
        ),
        f.Link(rel="stylesheet", href="assets/abop.css", type="text/css"),
    ),
)
operators = ["operator0", "operator1", "operator2"]


@rt("/")
def get():
    """
    Overview of operators
    """
    paragraphs = [f.H1("abstract"), f.H2("operators")]
    paragraphs += [f.Ul(o) for o in operators]
    paragraphs += [f.Footer("© 2024, abstract operators")]
    return (
        f.Title("abop title"),
        f.Div(*paragraphs),
        f.Card(
            "Operator Card",
            header="This is an Operator Card",
            footer="This is the content of the Operator Card",
        ),
    )


f.serve()
