from dotenv import dotenv_values
from openai import OpenAI

OPENAI_API_KEY = dotenv_values(".env")["OPENAI_API_KEY"]
client = OpenAI(api_key=OPENAI_API_KEY)

MODEL = "gpt-3.5-turbo-1106"

# Creates a new thread ever
thread = client.beta.threads.create()

assistant1 = client.beta.assistants.create(
    instructions="You are a web developer. You will create flask webpages. ",
    model=MODEL,
    tools=[{"type": "code_interpreter"}],
)

message = client.beta.threads.messages.create(
    thread_id=thread.id,
    role="user",
    content="'Hello World foobar this is a basic webpage'",
)

run = client.beta.threads.runs.create_and_poll(
    thread_id=thread.id,
    assistant_id=assistant1.id,
    instructions="Create the code for a quick startup flask webpage. The root path will return the users request as a string.",
)

if run.status == "completed":
    messages = client.beta.threads.messages.list(thread_id=thread.id)
    for message in messages:
        print(message)
else:
    print(run.status)

assistant3 = client.beta.assistants.create(
    instructions="You are a web development tester. You will write code to send HTTP requests, and return the results"