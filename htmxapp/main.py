from fasthtml import common as c

app, rt = c.fast_app()

operators = ['operator0', 'operator1', 'operator2']


@rt('/')
def get():
    """
    Overview of operators
    """
    pees = [c.H1('abstract'), c.H2('operators')]
    pees += [c.Ul(o) for o in operators]
    pees += [c.Footer("© 2024, abstract operators")]
    return c.Div(*pees, hx_get="/change")


c.serve()
