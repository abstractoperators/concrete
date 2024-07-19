import time
from textwrap import dedent
from typing import Any, List

from openai import OpenAI


class Agent:
    def __init__(self, client: OpenAI, model: str = "gpt-3.5-turbo-0125"):
        self.client = client
        self.assistant_id = client.beta.assistants.create(
            instructions="""You are a software developer. You will answer software development questions as concisely as possible.""",
            model=model,
        ).id


class Developer(Agent):
    def ask_question(self, context: str) -> str:
        thread = self.client.beta.threads.create()

        self.client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=dedent(
                f"""Context: 
                    {context}

                    If necessary, ask one essential question for continued implementation. If unnecessary, respond 'No Question'.  

                    Example:
                    Context:
                    1. Imported the Flask module from the flask package
                    Current Component: Create a Flask application instance

                    Response: No Question

                    Example:
                    Context:
                    1. The code imported the Flask module from the flask package
                    2. The code created a Flask application named "app"
                    3. Created a route for the root URL ('/')
                    Current Component: Create a function that will be called when the root URL is accessed. This function should return HTML with a temporary Title, Author, and Body Paragraph

                    Response: What should the function be called?"""  # noqa: E501
            ),
        )

        self.client.beta.threads.runs.create_and_poll(
            thread_id=thread.id, assistant_id=self.assistant_id
        )

        messages = self.client.beta.threads.messages.list(thread_id=thread.id)
        question = messages.data[0].content[0].text.value

        return question

    def implement_component(self, context: str) -> str:
        thread = self.client.beta.threads.create()

        self.client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=dedent(
                f"""
                Context:
                {context}

                Based on the context, provide code the current component. Never provide unspecified code.

                Example:
                Context:
                1. Imported the Flask module from the flask package
                Current Component: Create a flask application instance named 'app'
                Response: app = Flask(app)
                
                
                Example:
                Context:
                1. The code imported the Flask module from the flask package
                2. The code created a Flask application named "app"
                3. Created a route for the root URL ('/')
                Current Component: Create a function that will be called when the root URL is accessed. This function should return HTML with a temporary Title, Author, and Body Paragraph
                The function should be called index
                
                Response: 
                def index():
                    return '''
                    <!DOCTYPE html>
                    <html>
                        <head>
                            <title>Page Title</title>
                        </head># noqa: E501
                    <body>
                        <h1>Main Title</h1>
                        <h2>Authors:</h2>
                        <p>Author 1, Author 2</p>
                        <p>This is a body paragraph.</p>
                    </body>
                    </html>'''
                """  # noqa: E501
            ),
        )

        self.client.beta.threads.runs.create_and_poll(
            thread_id=thread.id, assistant_id=self.assistant_id
        )

        messages = self.client.beta.threads.messages.list(thread_id=thread.id)
        implementation = messages.data[0].content[0].text.value

        return implementation

    def integrate_components(
        self, implementations: List[str], webpage_idea: str
    ) -> str:
        thread = self.client.beta.threads.create()
        self.client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=f"""\nTask: Combine all these implementations into a single, coherent final application to {webpage_idea} Ensure that:
            
            1. All necessary imports are at the top of the file
            2. Code is organized logically
            3. There are no duplicate or conflicting code
            4. Resolve conflicting or redundant pieces of code. 
            5. Only code is returned
            """,
        )

        self.client.beta.threads.runs.create_and_poll(
            thread_id=thread.id, assistant_id=self.assistant_id
        )

        messages = self.client.beta.threads.messages.list(thread_id=thread.id)
        integrated_implementation = messages.data[0].content[0].text.value

        return integrated_implementation


class Executive(Agent):
    def answer_question(self, context: str, question: str) -> str:
        thread = self.client.beta.threads.create()

        self.client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=f"Context: {context} Developer's Question: {question}\n As the senior advisor, answer with specificity the developer's question about this component. If there is no question, then respond with 'Okay'. Do not provide clarification unprompted.",
        )
        self.client.beta.threads.runs.create_and_poll(
            thread_id=thread.id, assistant_id=self.assistant_id
        )

        messages = self.client.beta.threads.messages.list(thread_id=thread.id)
        answer = messages.data[0].content[0].text.value

        return answer

    def generate_summary(
        self, previous_components: List[str], implementation: str
    ) -> str:
        thread = self.client.beta.threads.create()

        self.client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=f"""Provide an explicit summary of what has been implemented as a list of points.
            
            Previous Components: {previous_components}
            Current Component Implementation: {implementation}

            For each component:
            1. Describe its functionality if necessary
            2. Include variable names if necessary
            3. Provide implementation details using natural language
            
            Example:
            1. imported the packages numpy and pandas as np and pd respectively. imported random
            2. Instantiated a pandas dataframe named foo, with column names bar and baz
            3. Populated foo with random ints
            4. Printed average of bar and baz
            """,
        )

        self.client.beta.threads.runs.create_and_poll(
            thread_id=thread.id, assistant_id=self.assistant_id
        )

        messages = self.client.beta.threads.messages.list(thread_id=thread.id)
        summary = messages.data[0].content[0].text.value
        return summary
