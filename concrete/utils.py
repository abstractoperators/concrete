"""AI generated"""

import ast
import re

import astor


class CommentAndDocstringRemover(ast.NodeTransformer):
    def visit_Module(self, node):
        # Remove module-level docstring if present
        if len(node.body) > 0 and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant):
            node.body.pop(0)
        return self.generic_visit(node)

    def visit_ClassDef(self, node):
        # Remove class-level docstring if present
        if len(node.body) > 0 and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant):
            node.body.pop(0)
        return self.generic_visit(node)

    def visit_FunctionDef(self, node):
        # Remove function-level docstring if present
        if len(node.body) > 0 and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant):
            node.body.pop(0)
        return self.generic_visit(node)

    def visit_Expr(self, node):
        # Remove standalone expressions that are actually comments
        if isinstance(node.value, ast.Constant):
            return None
        return self.generic_visit(node)


def remove_comments(source_code):
    # Parse the source code into an AST
    tree = ast.parse(source_code)

    # Transform the AST to remove comments and docstrings
    remover = CommentAndDocstringRemover()
    tree = remover.visit(tree)

    # Convert the AST back to source code
    modified_code = astor.to_source(tree)

    # Remove extra whitespace
    modified_code = remove_extra_whitespace(modified_code)

    return modified_code


def remove_extra_whitespace(code: str):
    # Preserve strings while removing extra whitespace
    string_regex = r"(\"\"\".*?\"\"\"|\'\'\'.*?\'\'\'|\".*?\"|\'.*?\')"

    # Extract strings and replace them with placeholders
    strings = re.findall(string_regex, code, re.DOTALL)
    placeholders = [f"__STRING_PLACEHOLDER_{i}__" for i in range(len(strings))]
    code_without_strings = re.sub(string_regex, lambda m: placeholders.pop(0), code, flags=re.DOTALL)

    # Remove extra whitespace outside of strings
    code_without_extra_whitespace = re.sub(r"\n\s*\n", "\n", code_without_strings)  # Remove empty lines
    code_without_extra_whitespace = re.sub(
        r"^\s+$", "", code_without_extra_whitespace, flags=re.MULTILINE
    )  # Remove lines with only whitespace

    # Reinsert the strings back into their placeholders
    for i, placeholder in enumerate(strings):
        code_without_extra_whitespace = code_without_extra_whitespace.replace(f"__STRING_PLACEHOLDER_{i}__", strings[i])

    return code_without_extra_whitespace
