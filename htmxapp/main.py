from fasthtml.common import Div, P, fast_app, serve

app, rt = fast_app()


@rt('/')
def get():
    return Div(P('Hello World!'), hx_get="/change")


serve()
