import unittest
from uuid import uuid4

from concrete_core.models.messages import TextMessage
from concrete_core.operators import Developer, Executive
from concrete_db.orm.models import Message as SQLModelMessage
from concrete_db.orm.models import Operator as SQLModelOperator
from concrete_db.orm.models import Project


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
            type='textmessage',
            content='{\n    "text": "print(\\"Hello, World!\\")"\n}',
            prompt="Make a helloworld script",
            status='completed',
            project_id=uuid4(),
            user_id=uuid4(),
            operator_id=uuid4(),
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
            id=uuid4(),
            title='developer',
            name='miguel',
            instructions='Instructions for developer operator',
        )
        sql_operator_developer.direct_message_project = Project(id=uuid4())
        pydantic_operator_developer = sql_operator_developer.to_obj()
        self.assertIsInstance(pydantic_operator_developer, Developer)
        self.assertEqual(pydantic_operator_developer.operator_id, sql_operator_developer.id)
        self.assertEqual(pydantic_operator_developer.instructions, sql_operator_developer.instructions)

        sql_operator_executive = SQLModelOperator(
            id=uuid4(),
            title='executive',
            name='kentavius',
            instructions='Instructions for executive operator',
        )
        sql_operator_executive.direct_message_project = Project(id=uuid4())
        pydantic_operator_executive = sql_operator_executive.to_obj()

        self.assertIsInstance(pydantic_operator_executive, Executive)
        self.assertEqual(pydantic_operator_executive.operator_id, sql_operator_executive.id)
        self.assertEqual(pydantic_operator_executive.instructions, sql_operator_executive.instructions)
