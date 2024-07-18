import time
from typing import Any, List

from openai import OpenAI

# TODO Replace run = self.client.beta.threads.runs.create(....
# + while True(sleep(1).... retrieve)
# with create_and_poll


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

        run = self.client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=self.assistant_id,
            instructions="Ask a specific question to clarify details about the current component",
        )

        while True:
            time.sleep(1)
            run_status = self.client.beta.threads.runs.retrieve(
                thread_id=thread.id, run_id=run.id
            )
            if run_status.status == "completed":
                break
            elif run_status.status == "failed":
                raise Exception("Run failed")

        messages = self.client.beta.threads.messages.list(thread_id=thread.id)
        question = messages.data[0].content[0].text.value

        return question

    def implement_component(self, context: str) -> str:
        thread = self.client.beta.threads.create()

        self.client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=f"Based on this context, provide code for ONLY the current component: {context}",
        )

        run = self.client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=self.assistant_id,
            instructions="Provide the code to implement only the current component based on the provided context and specifications. NEVER provide code unprompted",
        )

        while True:
            time.sleep(1)
            run_status = self.client.beta.threads.runs.retrieve(
                thread_id=thread.id, run_id=run.id
            )
            if run_status.status == "completed":
                break
            elif run_status.status == "failed":
                raise Exception("Run failed")

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
            """,
        )

        run = self.client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=self.assistant_id,
            instructions="Integrate all the provided implementations into a single, coherent application. Resolve any conflicts and ensure the final code is complete and ready to run. Return only the code",
        )

        while True:
            time.sleep(1)
            run_status = self.client.beta.threads.runs.retrieve(
                thread_id=thread.id, run_id=run.id
            )
            if run_status.status == "completed":
                break
            elif run_status.status == "failed":
                raise Exception("Run failed")

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
            content=f"Context: {context} Developer's Question: {question}\n As the senior advisor, answer with specificity the developer's question about this component. If there is no question, then do not respond. Do not provide unprompted information.",
        )

        run = self.client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=self.assistant_id,
            instructions="Answer the developer's question with specificity",
        )

        while True:
            time.sleep(1)
            run_status = self.client.beta.threads.runs.retrieve(
                thread_id=thread.id, run_id=run.id
            )
            if run_status.status == "completed":
                break
            elif run_status.status == "failed":
                raise Exception("Run failed")

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
            content="Provide an explicit summary of what has been implemented. Include only and all implemented components, and provide variable names and implementation details using natural language.",
        )

        run = self.client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=self.assistant_id,
            instructions=f"Summarize what has been implemented in the {previous_components}, and in the current component {implementation}",
        )

        while True:
            time.sleep(1)
            run_status = self.client.beta.threads.runs.retrieve(
                thread_id=thread.id, run_id=run.id
            )
            if run_status.status == "completed":
                break
            elif run_status.status == "failed":
                raise Exception("Run failed")

        messages = self.client.beta.threads.messages.list(thread_id=thread.id)
        summary = messages.data[0].content[0].text.value
        return summary
