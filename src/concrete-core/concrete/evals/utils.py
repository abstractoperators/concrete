from concrete.models.messages import Message, ProjectFile, Rating
from concrete.operators import Judge


def is_valid_python(projectfile: ProjectFile) -> bool:
    try:
        if projectfile.file_path.endswith(".py"):
            compile(projectfile.file_contents, projectfile.file_name, "exec")
            return True
        raise ValueError("File is not a python file")
    except SyntaxError:
        return False


def qna_llm_as_a_judge_middleware(query: str, message: Message) -> None:
    """
    Utility function for invoking a LLM as a Judge.
    """

    judge = Judge()
    rating: Rating = judge.rate_simple(query, str(message), options={'response_format': Rating})  # type: ignore # noqa
    # Do something with this rating ig
