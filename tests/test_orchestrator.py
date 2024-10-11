import unittest

from concrete.abstract import AbstractOperator
from concrete.operators import Operator

# Test Orchestrations
# Test that process_new_project returns an async gen?
# Test communicative_dehallucination?


# Test Operators
# Test that all operators inheriting from Operator have instructions
# Test Operator magic attaching qna to functions
# Test that all operators have a chat
# That the qna of operators has the correct output format


def get_all_subclasses(cls):
    subclasses = set()
    for subclass in cls.__subclasses__():
        subclasses.add(subclass)
        subclasses.update(get_all_subclasses(subclass))
    return subclasses


class MockOperator(AbstractOperator):
    def string_method(self):
        return "this is a string"

    def non_string_method(self):
        return 42


class TestOperator(unittest.TestCase):
    def test_operator_instructions(self):
        """
        Verify every class inheriting from Operator gets an string instructions attribute
        """
        subclasses = get_all_subclasses(Operator)
        for subclass in subclasses:
            self.assertIn(
                'instructions', subclass.__dict__, f"{subclass.__name__} must override the 'instructions' attribute"
            )
            instructions = subclass.__dict__['instructions']
            self.assertIsInstance(
                instructions, str, f"{subclass.__name__}'s 'instructions' attribute must be of type str"
            )

    def test_operator_qna(self):
        """
        Verify that subclasses of AbstractOperator have their string returning functions wrapped by qna.
        """

        class MockOperator(AbstractOperator):
            instructions = "Foo bar baz."

            def method_returning_str(self):
                return "This is a string."

            def method_returning_int(self):
                return 42

            def method_returning_none(self):
                return None

            def method_returning_list(self):
                return [1, 2, 3]

            def method_with_args(self, x=1, y=2):
                return f"Sum of {x} and {y} is {x + y}"

        string_methods = [
            'method_returning_str',
            'method_with_args',
        ]

        non_string_methods = [
            'method_returning_int',
            'method_returning_none',
            'method_returning_list',
        ]

        operator = MockOperator()

        def mock_qna(self, query, response_format, instructions=None):
            return f"Mocked: {query}"

        # Attach the mock qna to the operator
        operator._qna = mock_qna.__get__(operator, MockOperator)

        # Methods returning strings should be wrapped by qna, modifying the return value with
        # prefix 'Mocked: '
        for method_name in string_methods:
            method = getattr(operator, method_name)
            original_method = MockOperator.__dict__[method_name]
            unwrapped_result = original_method(operator)
            wrapped_result = method()
            self.assertEqual(
                f'Mocked: {unwrapped_result}',
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
