from fasthtml import common as f

app, rt = f.fast_app()

operators = ['operator0', 'operator1', 'operator2']


@rt('/')
def get():
    """
    Overview of operators
    """
    paragraphs = [f.H1('abstract'), f.H2('operators')]
    paragraphs += [f.Ul(o) for o in operators]
    paragraphs += [f.Footer("© 2024, abstract operators")]
    return f.Title("abop"), f.Div(*paragraphs, hx_get="/change")


f.serve()
