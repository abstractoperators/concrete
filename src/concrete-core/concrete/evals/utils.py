from concrete.models.messages import ProjectFile


def is_valid_python(projectfile: ProjectFile) -> bool:
    try:
        if projectfile.file_path.endswith(".py"):
            compile(projectfile.file_contents, projectfile.file_name, "exec")
            return True
        raise ValueError("File is not a python file")
    except SyntaxError:
        return False
