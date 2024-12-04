from concrete.models.messages import Message, ProjectFile, Rating
from concrete.operators import Judge


def is_valid_python(projectfile: ProjectFile) -> bool:
    """
    Utility function for checking if a projectfile is a valid python file.
    Returns True if the file compiles, False otherwise
    Raises a ValueError if the file extension is not .py
    """
    try:
        if projectfile.file_name.endswith(".py"):
            compile(projectfile.file_contents, projectfile.file_name, "exec")
            return True
        raise ValueError("File is not a python file")
    except SyntaxError:
        return False


def qna_llm_as_a_judge(query: str, message: Message) -> Rating:
    """
    Utility function for invoking a LLM as a Judge.
    """

    judge = Judge()
    rating: Rating = judge.rate_simple(query, str(message), options={'response_format': Rating})  # type: ignore # noqa

    return rating
