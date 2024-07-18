import time
from typing import Any, List

from openai import OpenAI


class Developer:
    def __init__(self, client: OpenAI, assistant_id: str):
        self.client = client
        self.assistant_id = assistant_id

    def ask_question(self, context: str) -> str:
        thread = self.client.beta.threads.create()

        self.client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=f"Context: {context}\n As the developer, if necessary to implement, ask a clarifying question about the current component. Otherwise, respond with No Question.",
        )

        run = self.client.beta.threads.runs.create_and_poll(
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
            content=f"Based on the context, provide code the current component. Never provide unspecified code: {context}",
        )

        run = self.client.beta.threads.runs.create_and_poll(
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

        run = self.client.beta.threads.runs.create_and_poll(
            thread_id=thread.id, assistant_id=self.assistant_id
        )

        messages = self.client.beta.threads.messages.list(thread_id=thread.id)
        integrated_implementation = messages.data[0].content[0].text.value

        return integrated_implementation


class Executive:
    def __init__(self, client: OpenAI, assistant_id: str):
        self.client = client
        self.assistant_id = assistant_id

    def answer_question(self, context: str, question: str) -> str:
        thread = self.client.beta.threads.create()

        self.client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=f"Context: {context} Developer's Question: {question}\n As the senior advisor, answer with specificity the developer's question about this component. If there is no question, then respond with 'Okay'. Do not provide clarification unprompted.",
        )
        run = self.client.beta.threads.runs.create_and_poll(
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

        run = self.client.beta.threads.runs.create_and_poll(
            thread_id=thread.id, assistant_id=self.assistant_id
        )

        messages = self.client.beta.threads.messages.list(thread_id=thread.id)
        summary = messages.data[0].content[0].text.value
        return summary
