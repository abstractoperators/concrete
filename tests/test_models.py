import unittest

from concrete.db.orm.models import Message as SQLModelMessage
from concrete.db.orm.models import Operator as SQLModelOperator
from concrete.models.messages import TextMessage
from concrete.operators import Developer, Executive


class TestSQLModels(unittest.TestCase):
    """
    Test that SQLModels can be created from and dumped back to their original Pydantic models.
    """

    def test_message(self):
        """
        Test that a concrete.models.messages.Message can be created from a
        SQLModel Message concrete.db.orm.models.Message
        """
        sql_message_text = SQLModelMessage(
            type_name='textmessage',
            content='{\n    "text": "print(\\"Hello, World!\\")"\n}',
            prompt="Make a helloworld script",
            status='completed',
            project_id=1,
            user_id=1,
            operator_id=1,
        )

        pydantic_message_text = sql_message_text.to_obj()
        self.assertIsInstance(pydantic_message_text, TextMessage)
        self.assertEqual(pydantic_message_text.text, "print(\"Hello, World!\")")

    def test_operator(self):
        """
        Test that a concrete.models.operators.Operator can be created from a
        SQLModel Operator concrete.db.orm.models.Operator
        """
        sql_operator_developer = SQLModelOperator(
            id=1,
            title='developer',
            instructions='Instructions for developer operator',
        )

        pydantic_operator_developer = sql_operator_developer.to_obj()
        self.assertIsInstance(pydantic_operator_developer, Developer)
        self.assertEqual(pydantic_operator_developer.operator_id, sql_operator_developer.id)
        self.assertEqual(pydantic_operator_developer.instructions, sql_operator_developer.instructions)

        sql_operator_executive = SQLModelOperator(
            id=2,
            title='executive',
            instructions='Instructions for executive operator',
        )
        pydantic_operator_executive = sql_operator_executive.to_obj()

        self.assertIsInstance(pydantic_operator_executive, Executive)
        self.assertEqual(pydantic_operator_executive.operator_id, sql_operator_executive.id)
        self.assertEqual(pydantic_operator_executive.instructions, sql_operator_executive.instructions)
