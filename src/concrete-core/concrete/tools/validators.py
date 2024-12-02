from concrete.models.messages import ProjectFile, Rating, TextMessage
from concrete.validators.utils import is_valid_python, qna_llm_as_a_judge_middleware

from .meta import MetaTool


class ValidatePython(metaclass=MetaTool):
    @classmethod
    def is_valid_python(cls, file_name: str, file_contents: str) -> bool:
        """
        file_name (str): The name of the file + extension.
        file_contents (str): The full contents of the file.
        """
        project_file = ProjectFile(
            file_name=file_name,
            file_contents=file_contents,
        )
        return is_valid_python(project_file)


class LMAsJudge(metaclass=MetaTool):
    @classmethod
    def rate_message(cls, query: str, message: str) -> Rating:
        """
        query (str): The query to rate the message against.
        message (str): The message to rate.
        """

        return qna_llm_as_a_judge_middleware(query, TextMessage(text=message))
