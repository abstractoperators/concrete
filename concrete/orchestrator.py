import os
import time
from typing import List, Tuple

from assistants import Developer, Executive
from dotenv import load_dotenv
from openai import OpenAI


def communicative_dehallucination(
    executive: Executive,
    developer: Developer,
    summary: str,
    component: str,
    max_iter: int = 1,
) -> Tuple[str, str, str]:
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
            - context (str): The full context including all Q&A pairs.
            - summary (str): A concise summary of what has been achieved for this component.
    """

    context = f"""
    Previous Components summarized: {summary}
    Current Component: {component}
    """
    print(f"Context: \n{context}\n")

    # Iterative Q&A process
    for i in range(max_iter):
        # Developer asks a question
        question = developer.ask_question(context)
        print(f"Developer's question:\n {question}\n")

        # Executive answers the question
        answer = executive.answer_question(context, question)
        print(f"Executive's answer:\n {answer}\n")

        # Update context with new Q&A pair
        context += f"\n {i+1}: Clarifying Question about current component: {question}\n Clarifying Answer about current component: {answer}\n"

    # Developer implements component based on clarified context
    implementation = developer.implement_component(context)
    print(f"Current Component Implementation:\n{implementation}\n")

    # Generate a summary of what has been achieved
    summary = executive.generate_summary(summary, implementation)
    print(f"Summary: {summary}")

    return implementation, context, summary


def main() -> None:
    load_dotenv()
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    client = OpenAI(api_key=OPENAI_API_KEY)

    GPT_MODEL = "gpt-3.5-turbo-1106"
    WEBPAGE_IDEA = "Provide the code to quickstart a basic builtin Flask server. The Flask server should only show Hello World"

    print("Creating assistants")
    executive = client.beta.assistants.create(
        name="Executive",
        instructions="You are a senior software developer. You break down tasks and provide high-level instructions using natural language.",
        model=GPT_MODEL,
    )

    developer = client.beta.assistants.create(
        name="Developer",
        instructions="You are a web developer. You create and deploy Flask webpages based on instructions, asking questions when necessary",
        model=GPT_MODEL,
    )

    developer_assistant = Developer(client, developer.id)
    executive_assistant = Executive(client, executive.id)

    thread = client.beta.threads.create()
    initial_prompt = client.beta.threads.messages.create(
        thread_id=thread.id, role="user", content=WEBPAGE_IDEA
    )

    print("Defining project components")
    run = client.beta.threads.runs.create_and_poll(
        thread_id=thread.id,
        assistant_id=executive.id,
        instructions="""
        List, in natural language, only the essential code components needed to fulfill the user's request.
    
        Your response must:
        1. Include only core components.
        2. Put each new component on a new line (not numbered).
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
        1. [Natural language specification of the specific code component or function call]
        2. [Natural language specification of the specific code component or function call]
        ...
        """,
    )

    if run.status == "completed":
        messages = client.beta.threads.messages.list(thread_id=thread.id)
    else:
        print(run.status)

    # Parse the components from the executive's response
    messages = client.beta.threads.messages.list(thread_id=thread.id)

    message = client.beta.threads.messages.retrieve(
        thread_id=thread.id, message_id=messages.data[0].id
    )
    components = message.content[0].text.value.split("\n")
    components = [comp.strip() for comp in components if comp.strip()]
    print("Components to be implemented:")
    print(components)
    # Initialize previous_components
    summary = ""
    all_implementations = []

    for i, component in enumerate(components):
        print(f"\nProcessing Component {i+1}: \n{component}")

        # Use communicative_dehallucination for each component
        implementation, context, summary = communicative_dehallucination(
            executive_assistant, developer_assistant, summary, component, max_iter=1
        )

        # Add the implementation to our list
        all_implementations.append(implementation)

        final_code = developer_assistant.integrate_components(
            all_implementations, WEBPAGE_IDEA
        )

    print(final_code)


if __name__ == "__main__":
    main()
