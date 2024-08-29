from abc import abstractmethod
from functools import wraps
from textwrap import dedent
from typing import Callable, List
from uuid import uuid1

from celery import Task, signals
from pydantic import BaseModel

from .clients import CLIClient, Client
from .models.responses import TextResponse
from .tools import MetaTool


class LlmMixin(Task):
    """
    Represents the base Operator for further implementation.
    """

    def __init__(
        self,
        clients: dict[str, Client],
        tools: list[MetaTool] | None = None,
    ):
        super().__init__()
        self.uuid = uuid1()
        self.clients = clients
        self.tools = tools
        # Question: What is this for?
        signals.worker_init.connect(self.on_worker_init)

    @property
    @abstractmethod
    def instructions(self) -> str:
        """
        Define the operators base instructions.

        Used in LlmMixin.qna
        """
        pass

    @property
    def clients(self):
        return self._clients

    def on_worker_init(self, *args, **kwargs):
        self._clients: dict[str, Client] = kwargs['clients']

    def _qna(
        self,
        query: str,
        response_format: BaseModel | None = None,
    ) -> BaseModel:
        """
        "Question and Answer", given a query, return an answer.
        Basically just a wrapper for OpenAI's chat completion API.

        Synchronous.
        """
        instructions = self.instructions
        instructions += "\nIf you are provided tools, use them as specified, otherwise leave them blank."
        instructions += "\nFor each user request: Think about the response syntax, and how that relates to your task. Then, provide a complete and accurate response."  # noqa E501
        messages = [
            {'role': 'system', 'content': instructions},
            {'role': 'user', 'content': query},
        ]

        response = (
            self.clients["openai"]
            .complete(
                messages=messages,
                response_format=response_format if response_format else TextResponse,
            )
            .choices[0]
        ).message

        if response.refusal:
            CLIClient(f"Operator refused to answer question: {query}")
            raise Exception("Operator refused to answer question")

        answer = response.parsed

        CLIClient.emit(query)
        return answer

    @classmethod
    def qna(cls, question_producer: Callable) -> Callable:
        """
        Decorate something on a child object downstream to get a response from a query.

        question_producer is expected to return a request like "Create a website that does xyz"

        The decorated function will support some extra optionality:

        response_format (BaseModel): Guarantee a json structured output.
        tools (list[MetaTool]): Pass in tools for the operator to use. Supercedes use_tools
        use_tools (bool): Prompt the operator to use tools that it has.
        """

        @wraps(question_producer)
        def _send_and_await_reply(*args, **kwargs):
            self = args[0]
            # TODO: change response_format based on if use_tools is toggled
            response_format = kwargs.pop("response_format", None)

            # Use `tools=...` if provided, otherwise check `use_tools` and use `self.tools` if True
            tools = (
                explicit_tools
                if (explicit_tools := kwargs.pop("tools", []))
                else (self.tools if kwargs.pop('use_tools', False) else [])
            )

            query = question_producer(*args, **kwargs)

            # Add additional prompt to inform agent about tools
            if tools:
                # LLMs don't really know what should go in what field even if output struct
                # is guaranteed
                query += """Here are your available tools:\
    Either call the tool with the specified syntax, or leave its field blank.\n"""
                for tool in tools:
                    query += str(tool)
            return self._qna(query, response_format=response_format)

        return _send_and_await_reply


class Operator(LlmMixin):
    instructions = (
        "You are an autonomous abstract operator designed to be "
        "a helpful, proactive, curious, and thoughtful employee or assistant. "
        "You'll be given additional to complete a task. "
        "You will clearly state if a task is beyond your capabilities. "
    )

    @LlmMixin.qna
    def chat(cls, message: str) -> str:
        """
        Chat with the operator with a direct message.
        """
        return message


class Developer(Operator):
    """
    Represents an Operator that produces code.
    """

    instructions = (
        "You are an expert software developer. You will follow the instructions given to you to complete each task."
    )

    """
        You are a senior software engineer at an innovative AI agent orchestration startup. Your deep
        understanding of software architecture, AI systems, and scalable solutions empowers you to design
        and implement cutting-edge technologies that enhance AI capabilities.
        Objective:
        Your task is to apply your expertise to architect and optimize AI agent orchestration frameworks, ensuring high performance, scalability, and reliability. You will be working on complex systems that integrate multiple AI agents, enabling them to collaborate efficiently to achieve sophisticated goals.
        Leverage your technical expertise to create robust, scalable, and innovative AI agent orchestration systems. Apply clarity, completeness, specificity, adaptability, and creativity to deliver high-quality, impactful solutions.
    """  # noqa E501

    @LlmMixin.qna
    def ask_question(self, context: str) -> str:
        """
        Accept instructions and ask a question about it if necessary.

        Can return `no question`.
        """
        return dedent(
            f"""
            *Context:*
            {context}

            If necessary, ask one essential question for continued implementation.
            If no question is necessary, respond 'No Question'.

            **Example:**
                Context:
                1. Imported the Flask module from the flask package
                Current Component: Create a Flask application instance
                Clarification: None

                No Question


            **Example:**
                Context:
                1. The code imported the Flask module from the flask package
                2. The code created a Flask application named "app"
                3. Created a route for the root URL ('/')
                Current Component: Create a function that will be called when the root URL is accessed.\
                This function should return HTML with a temporary Title, Author, and Body Paragraph

                What should the function be called?"""
        )

    @LlmMixin.qna
    def implement_component(self, context: str) -> str:
        """
        Prompts the Operator to implement a component based off of the components context.
        Returns the code for the component
        """
        return f"""
Provide complete and accurate code for the current component only. Your code for the current component will be used to implement the initial prompt.\
Use placeholders referencing code/functions already provided in the context. Never provide unspecified code.
*Context:*
{context}"""  # noqa E501

    @LlmMixin.qna
    def integrate_components(
        self,
        planned_components: List[str],
        implementations: List[str],
        idea: str,
    ) -> str:
        """
        Prompts Operator to combine code implementations of multiple components
        Returns the combined code
        """
        prev_components = []
        for desc, code in zip(planned_components, implementations):
            prev_components.append(
                f"\nComponent description: {desc}\nImplementation\nFile: {code.file_name}\nFile Contents:\n{code.file_contents}\n"  # noqa E501
            )

        out_str = f"""\
Task: Use ALL of the provided components to implement the original idea. Include every provided file.
Idea: {idea}

First, think about all files you intend to use in the final output. Then, combine the code from each component into those files.
**Components:**
    {"".join(prev_components)}
            """  # noqa E501
        return out_str

    @LlmMixin.qna
    def implement_html_element(self, prompt: str) -> str:
        out_str = f"""\
Generate an html element with the following description:\n
{prompt}

Generated html elements should be returned as a string with the following format.
Remember to ONLY return the generated HTML element. Do not include any other information.

Example 1.
Generate an html element with the following description:
A header that says `Title`

<h1>Title</h1>

Example 2.
Generate an html element with the following description:
An input form with a submit button

<form method="POST" action="/">
<label for="textInput">Input:</label>
<input type="text" id="textInput" name="textInput" required>
<button type="submit">Submit</button>
</form>

Example 3.
Generate an html element with the following description:
Create a paragraph with the text `Hello, World!`

<p>Hello, World!</p>
"""
        return out_str


class Executive(Operator):
    """
    Represents an Operator that instructs and guides other Operators.
    """

    instructions = (
        "You are an expert executive software developer."
        "You will follow the instructions given to you to complete each task."
    )

    """
        You are an executive at a cutting-edge AI agent orchestration startup.
        Your strategic vision and leadership drive the company’s mission to revolutionize
        how AI agents collaborate, enabling transformative solutions across industries.
    """
    """
        Objective:
        Your task is to guide the overall strategy and vision for the company, ensuring
        that the organization’s AI agent orchestration platforms are not only technically
        superior but also aligned with market needs, customer expectations, and long-term
        growth objectives.
    """

    @LlmMixin.qna
    def plan_components(self, starting_prompt) -> str:
        return """\
List the essential code components required to implement the project idea. Each component should be atomic, \
such that a developer could implement it in isolation provided placeholders for preceding components.

Your responses must:
1. Include specific components
2. Be comprehensive, accurate, and complete
3. Use technical terms appropriate for the specific programming language and framework
4. Sequence components logically, with later components dependent on previous ones
5. Not include implementation details or code snippets
6. Assume all dependencies are already installed but NOT imported
7. Be decisive and clear, avoiding ambiguity or vagueness
8. Be declarative, using action verbs to describe the component.

Project Idea:
{starting_prompt}
        """.format(
            starting_prompt=starting_prompt
        )

    @LlmMixin.qna
    def answer_question(self, context: str, question: str) -> str:
        """
        Prompts the Operator to answer a question
        Returns the answer
        """
        return (
            f"Context: {context} Developer's Question: {question}\n"
            "As the senior advisor, answer with specificity the developer's question about this component."
            "If there is no question, then respond with 'Okay'. Do not provide clarification unprompted."
        )

    @LlmMixin.qna
    def generate_summary(self, summary: str, implementation: str) -> str:
        """
        Generates a summary of completed components
        Returns the summary
        """
        prompt = f"""Summarize what has been implemented in the current component. Append it to the list of previously summarized components.

For its summary:
1. Include file name, function name, and variable names.
2. Objectively summarize the component's purpose and functionality.
3. Be concise and clear.

Example Syntax:
1. Imported numpy as np from the numpy package in the file 'main.py'
2. Created a function named 'calculate_mean' that calculates the mean of a np.array in the file 'util.py'
3. Imported the 'calculate_mean' function in the file 'main.py'
3. Instantiated a variable 'foo' as an np.array in the file 'main.py'
4. Used calculate_mean to calculate the mean of 'foo' in the file 'main.py'

Current Component Implementation: {implementation}
Previous Components: {summary}"""  # noqa E501
        return prompt


class PromptEngineer(Operator):
    instructions = """
You are a world-class AI prompt engineer. Your task is to create base prompts that will guide other AI agents in producing high-quality, reliable, and innovative results.
These prompts are not meant to be self-contained. It is merely a persona an AI agent will adopt while processing an explicit instruction that will be added to the base prompt later.

Consider the following framework as you develop your prompts:

    1.	Clarity: Ensure your prompts are easy to understand and unambiguous. Unambiguous and easy to understand, ensuring that the AI knows exactly what is expected.
    2.	Completeness: Include all necessary information and context so the AI can respond comprehensively. Including all relevant information and context to allow for a thorough response.
    3.	Specificity: Be precise in your instructions, guiding the AI towards a specific outcome.  Guiding the AI towards a precise outcome or set of actions, reducing the likelihood of irrelevant results.
    4.	Adaptability: Create prompts that can be easily adapted to different contexts or adjusted as needed. Flexible enough to be used in various contexts or adjusted as necessary without losing effectiveness.
    5.	Creativity: Encourage the AI to explore creative and innovative solutions. Encouraging the AI to think outside the box and explore innovative solutions.

Using this framework, craft prompts that will empower AI agents to deliver the best possible outputs, whether for creative tasks, technical tasks, or any other type of challenge.

Condensed Summary of the Prompt Evaluation Framework:

“Ensure clarity, completeness, specificity, adaptability, and creativity in every prompt you design.”

Core instructions:
“Craft your prompts using this framework to produce the highest quality AI outputs.”
        """  # noqa E501


class ProductManager(Operator):
    instructions = """
As the Product Manager for our AI Agent Orchestration startup, your mission is to conceptualize and drive. the development of innovative features that streamline the coordination of multiple AI agents to achieve complex tasks. Your work involves translating high-level business objectives into actionable product roadmaps, ensuring that our platform remains intuitive, efficient, and scalable.
"""  # noqa E501


class Designer(Operator):
    instructions = """
As an AI orchestrator, your task is to conceptualize and design intuitive, user-friendly interfaces and workflows that enable seamless interaction between AI agents and users. Your designs should prioritize clarity, ensuring that users can easily understand and navigate the system, and completeness, providing all necessary components and information for a comprehensive user experience.

Your designs should be specific in addressing user needs, guiding the user through each step with precision, and adaptable, allowing for easy adjustments or extensions as the AI orchestration platform evolves. Finally, foster creativity in your designs, exploring innovative ways to enhance user engagement and the efficiency of AI-agent interactions.
    """  # noqa E501


class Salesperson(Operator):
    instructions = """
        You are a top-tier salesperson at a leading AI agent orchestration startup. Your role is to communicate the transformative potential of our AI solutions to prospective clients, emphasizing how our technology can seamlessly integrate into their operations to enhance efficiency, drive innovation, and boost their bottom line.
    """  # noqa E501
