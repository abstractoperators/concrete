from concrete.tools import MetaTool


class Arithmetic(metaclass=MetaTool):
    @classmethod
    def add(cls, x: int, y: int) -> int:
        """
        x (int): The first number
        y (int): The second number

        Returns the sum of x and y
        """
        return x + y

    @classmethod
    def subtract(cls, x: int, y: int) -> int:
        """
        x (int): The first number
        y (int): The second number

        Returns the difference of x and y
        """
        return x - y
