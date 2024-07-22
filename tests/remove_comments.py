import ast
import re
import sys
from textwrap import dedent


class DocstringRemover(ast.NodeTransformer):
    def visit_FunctionDef(self, node):
        node.body = [
            n
            for n in node.body
            if not isinstance(n, ast.Expr) or not isinstance(n.value, ast.Constant)
        ]
        return node

    def visit_ClassDef(self, node):
        node.body = [
            n
            for n in node.body
            if not isinstance(n, ast.Expr) or not isinstance(n.value, ast.Constant)
        ]
        return node

    def visit_Module(self, node):
        node.body = [
            n
            for n in node.body
            if not isinstance(n, ast.Expr) or not isinstance(n.value, ast.Constant)
        ]
        return node


def remove_comments(source_code):
    # Converting to a tree removes all comments
    tree = ast.parse(source_code)

    # But does not remove comments via multiline string.
    # Overload the visit_* methods which are called when the tree is unparsed so only expressions and constants are kept.
    transformer = DocstringRemover()
    modified_tree = transformer.visit(tree)
    cleaned_code = ast.unparse(modified_tree)

    # Remove all whitespace lines
    cleaned_code = "\n".join(line for line in cleaned_code.splitlines() if line.strip())

    return dedent(cleaned_code)


if __name__ == "__main__":
    input_file = sys.argv[1]

    with open(input_file, "r") as f:
        source_code = f.read()

    cleaned_code = remove_comments(source_code)

    print(cleaned_code)

    # RANDOM COMMENTS TO TEST
    should_not_be_removed = """hello\n'''world'''"""
    """
    should be 
    removed
    """
    remove_end = 0  # this is a comment
    """hello"""
    thisisastring = "thhisisa string"

    def test():  # hello
        def test2():
            pass

        return None  # world
