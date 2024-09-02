# Concrete

## Installation
```python
pip install concrete-operators
```

## Quickstart
```bash
export OPENAI_API_KEY=<your-api-key-here>
python -m concrete prompt "Create a simple program that says 'Hello, World!'"
```

## Dev Setup
Run the following commands to get your local environment setup
```bash
brew install poetry
poetry install
poetry shell
pre-commit install
```

Pre-commit will check for code formatting before completing the commit. If code is formatted by black, you will need to add the changes files to staged and re-try the commit.
Flake8 generally have to be handled manually.

To force a commit locally add the flag `--no-verify` as an option to `git commit` e.g. `git commit --no-verify -m "..."`. Github workflows should mirror local pre commit checks. After a --no-verify, you should run a `pre-commit run --all-files` to ensure that the code is formatted correctly before commiting, as pre-commit checks will not run on unchanged files.


## Celery Information
To run the celery worker, run ```make celery```. This command will also start rabbitmq, the message broker. You can also manually start the message broker by running ```make rabbitmq```

```make helloworld_celery``` will run a simple celery task to test that everything is running correcetly.

To run operator methods through celery, run `operator.foo.delay(kwargs).get()`. 
```python
from concrete import clients, operators

c = {'openai': clients.OpenAIClient(temperature=0)}
message="How moral is world domination if you're good"
resp: ConcreteChatCompletion = operators.Operator(c).chat.delay(message=message).get()
print(resp.text)
# print(resp.message.text)  # also works
```

It is important that arguments are keyword arguments. This returns a ConcreteChatCompletion object. message_format has been added to this object to allow for client-side validation into a message format via `ConcreteChatCompletion.message`.