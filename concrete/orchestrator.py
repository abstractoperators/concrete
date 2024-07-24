import os
from textwrap import dedent
from typing import Tuple

from dotenv import load_dotenv
from openai import OpenAI

from concrete.agents import Developer, Executive


def communicative_dehallucination(
    executive: Executive,
    developer: Developer,
    summary: str,
    component: str,
    max_iter: int = 1,
) -> Tuple[str, str]:
    """
    Implements a communicative dehallucination process for software development.

    Args:
        executive (Executive): The executive assistant object for answering questions.
        developer (Developer): The developer assistant object for asking questions and implementing.
        summary (str): A summary of previously implemented components.
        component (str): The current component to be implemented.
        max_iter (int, optional): Maximum number of Q&A iterations.

    Returns:
        tuple: A tuple containing:
            - implementation (str): The generated implementation of the component.
            - summary (str): A concise summary of what has been achieved for this component.
    """

    context = dedent(
        f"""Previous Components summarized:\n{summary}
    Current Component: {component}"""
    )
    print(f"Context: \n{context}\n")

    # Iterative Q&A process
    q_and_a = []
    for i in range(max_iter):
        # Developer asks a question
        question = developer.ask_question(context)
        print(f"Developer's question:\n {question}\n")

        if question == "No Question":
            break

        # Executive answers the question
        answer = executive.answer_question(context, question)
        print(f"Executive's answer:\n {answer}\n")

        q_and_a.append((question, answer))
        # Update context with new Q&A pair

    if q_and_a:
        context += "\nComponent Clarifications:"
        for question, answer in q_and_a:
            context += f"\nQuestion: {question}"
            context += f"\nAnswer: {answer}"

    # Developer implements component based on clarified context
    implementation = developer.implement_component(context)
    print(f"Current Component Implementation:\n{implementation}\n")

    # Generate a summary of what has been achieved
    summary = executive.generate_summary(summary, implementation)
    print(f"Summary: {summary}")

    return implementation, summary


def main(prompt: str) -> str:
    """
    Produces code based off of a prompt
    """
    load_dotenv()
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    client = OpenAI(api_key=OPENAI_API_KEY)

    print("Creating assistants...")

    developer_assistant = Developer(client)
    executive_assistant = Executive(client)

    thread = client.beta.threads.create()
    client.beta.threads.messages.create(thread_id=thread.id, role="user", content=prompt)

    print("Defining project components...")
    client.beta.threads.runs.create_and_poll(
        thread_id=thread.id,
        assistant_id=executive_assistant.assistant_id,
        instructions="""
        List, in natural language, only the essential code components needed to fulfill the user's request.
 
        Your response must:
        1. Include only core components.
        2. Put each new component on a new line (not numbered, but conceptually sequential).
        3. Focus on the conceptual steps of specific code elements or function calls
        4. Be comprehensive, covering all necessary components
        5. Use technical terms appropriate for the specific programming language and framework.
        6. Naturally sequence components, so that later components are dependent on previous ones.
 
        Important:
        - Assume all dependencies are already installed but not imported.
        - Do not include dependency installations.
        - Focus solely on the code components needed to implement the functionality.
        - NEVER provide code example
        - ALWAYS ensure all necessary components are present
 
        Example format:
        [Natural language specification of the specific code component or function call]
        [Natural language specification of the specific code component or function call]
        ...
        """,
    )

    messages = client.beta.threads.messages.list(thread_id=thread.id, order="desc", limit=1)
    components = messages.data[0].content[0].text.value.split("\n")
    components = [comp.strip() for comp in components if comp.strip()]
    print("Components to be implemented:")
    for component in components:
        print(component)

    summary = ""
    all_implementations = []

    for component in components:
        print(f"\nProcessing Component: {component}")

        # Use communicative_dehallucination for each component
        implementation, summary = communicative_dehallucination(
            executive_assistant, developer_assistant, summary, component, max_iter=1
        )

        # Add the implementation to our list
        all_implementations.append(implementation)

        final_code = developer_assistant.integrate_components(all_implementations, prompt)

    print(
        dedent(
            f"""Final Produced Code:
         {final_code}
         """
        )
    )
    return final_code
