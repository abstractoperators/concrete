import unittest

from concrete.abstract import AbstractOperator
from concrete.operators import Operator


def get_all_subclasses(cls):
    subclasses = set()
    for subclass in cls.__subclasses__():
        subclasses.add(subclass)
        subclasses.update(get_all_subclasses(subclass))
    return subclasses


class TestOperator(unittest.TestCase):
    def test_operator_instructions(self):
        """
        Verify every class inheriting from Operator gets an string instructions attribute
        """
        subclasses = get_all_subclasses(Operator)
        for subclass in subclasses:
            self.assertIn(
                "instructions",
                subclass.__dict__,
                f"Attribute `instructions` must be defined on {subclass.__name__}",
            )
            instructions = subclass.__dict__["instructions"]
            self.assertIsInstance(
                instructions,
                str,
                f"{subclass.__name__}'s 'instructions' attribute must be of type str",
            )

    def test_operator_chat(self):
        """
        Verify every class inheriting from AbstractOperator gets a chat method.
        """
        subclasses = get_all_subclasses(AbstractOperator)
        for subclass in subclasses:
            # Ensure that each subclass has a 'chat' method
            self.assertIn(
                "chat",
                dir(subclass),
                f"Subclass '{subclass.__name__}' does not implement a 'chat' method. Existing methods: {dir(subclass)}",
            )

    def test_operator_qna(self):
        """
        Verify that subclasses of AbstractOperator have their string returning functions wrapped by qna.
        """

        class MockOperator(AbstractOperator):
            instructions = "Foo bar baz."

            def method_returning_str(self, options={}):
                return "This is a string."

            def method_returning_int(self, **kwargs):
                return 42

            def method_returning_none(self, **kwargs):
                return None

            def method_returning_list(self, **kwargs):
                return [1, 2, 3]

            def method_with_args(self, x=1, y=2, options={}):
                return f"Sum of {x} and {y} is {x + y}"

        string_methods = [
            "method_returning_str",
            "method_with_args",
        ]

        non_string_methods = [
            "method_returning_int",
            "method_returning_none",
            "method_returning_list",
        ]

        operator = MockOperator()

        def mock_qna(self, query, response_format, instructions=None):
            return f"Mocked: {query}"

        # Attach the mock qna to the operator
        MockOperator._qna = mock_qna

        # Methods returning strings should be wrapped by qna, modifying the return value with
        # prefix 'Mocked: '
        for method_name in string_methods:
            method = getattr(operator, method_name)
            original_method = MockOperator.__dict__[method_name]
            unwrapped_result = original_method(operator)
            wrapped_result = method()
            self.assertEqual(
                f"Mocked: {unwrapped_result}",
                wrapped_result,
                f"Method '{method_name}' should invoke _qna and return the mocked response",
            )

        # Methods not returning string should not be wrapped by qna.
        # The return value should be the same as the original method
        for method_name in non_string_methods:
            method = getattr(operator, method_name)
            original_method = MockOperator.__dict__[method_name]
            unwrapped_result = original_method(operator)
            wrapped_result = method()
            self.assertEqual(
                unwrapped_result,
                wrapped_result,
                f"Method '{method_name}' should not invoke _qna and return the original response",
            )
