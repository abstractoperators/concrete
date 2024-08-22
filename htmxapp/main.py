from fasthtml.common import Div, P, fast_app, serve

app, rt = fast_app()

operators = ['operator0', 'operator1', 'operator2']


@rt('/')
def get():
    pees = [P(o) for o in operators]
    return Div(*pees, hx_get="/change")


serve()
