from concrete.utils import remove_comments


def test_remove_comments():
    source_code = \
'''"""
Module-level docstring.
"""

class ExampleClass:
    """
    This is a class docstring.
    """
    def example_method(self):
        """
        This is a method docstring.
        """
        # This is an inline comment
        
        
        print("Hello, \\nworld!")  # This is another inline comment

def another_function():
    """This is another function docstring."""
    return 42

# A function with extra newlines and spaces
def func_with_whitespace():
    
    print("Inside function")    
     
    x = 10
    
    y = 20
    
    return x + y
    
'''
    expected = \
'''class ExampleClass:
    def example_method(self):
        print('Hello, \\nworld!')
def another_function():
    return 42
def func_with_whitespace():
    print('Inside function')
    x = 10
    y = 20
    return x + y
'''
    actual = remove_comments(source_code)
    print("ACTUAL")
    print(actual)
    print("EXPECTED")
    print(expected)
    assert actual == expected