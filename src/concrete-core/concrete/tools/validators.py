from concrete.models.messages import ProjectFile, Rating, TextMessage
from concrete.validators.utils import is_valid_python, qna_llm_as_a_judge

from .meta import MetaTool


class ValidatePython(metaclass=MetaTool):
    @staticmethod
    def is_valid_python(file_name: str, file_contents: str) -> bool:
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
    @staticmethod
    def rate_message(query: str, message: str) -> Rating:
        """
        query (str): The query to rate the message against.
        message (str): The message to rate.
        """

        return qna_llm_as_a_judge(query, TextMessage(text=message))
