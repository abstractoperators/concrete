import os
from typing import Any, TypeVar

import requests
import requests.adapters
from openai import OpenAI, RateLimitError
from openai.types.chat import ChatCompletion
from pydantic import BaseModel as PydanticModel
from requests.adapters import HTTPAdapter, Retry
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

from .models.messages import Message, TextMessage


class Client:
    pass


Client_con = TypeVar("Client_con", bound=Client, contravariant=True)


class OpenAIClient(Client):
    """
    Thin wrapper around open AI client
    """

    def __init__(self, model: str | None = None, temperature: float | None = None):
        OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.default_temperature = temperature if temperature is not None else float(os.getenv("OPENAI_TEMPERATURE", 0))
        self.model = model or "gpt-4o-mini"

    @retry(
        wait=wait_random_exponential(min=1, max=60),
        stop=stop_after_attempt(6),
        retry=retry_if_exception_type(RateLimitError),
        reraise=True,
    )
    def complete(
        self,
        messages: list[dict[str, str]],
        message_format: type[Message] | dict = TextMessage,
        temperature: float | None = None,
        **kwargs,
    ) -> ChatCompletion:

        request_params = {
            "messages": messages,
            "model": self.model,
            "temperature": temperature if temperature is not None else self.default_temperature,
            "response_format": message_format,
            **kwargs,
        }

        try:
            # Pydantic Model
            if isinstance(message_format, type(Message)):
                return self.client.beta.chat.completions.parse(**request_params)
            # JSON Schema
            return self.client.chat.completions.create(**request_params)
        except RateLimitError as e:
            print(f"Rate limit error: {e}")
            raise e  # retry decorator

    @staticmethod
    def model_to_schema(model: type[PydanticModel]) -> dict[str, str | dict]:
        """
        Utility for formatting a pydantic model into a json output for OpenAI.
        """
        return {
            "type": "json_schema",
            "json_schema": {
                "name": model.__name__,
                "schema": model.model_json_schema(),
            },
        }


class CLIClient(Client):
    @classmethod
    def emit(cls, content: Any):
        if os.environ.get("ENV") != "PROD":
            print(str(content))


class HTTPClient(Client, requests.Session):
    """
    Set up requests.session to access
    """

    def __init__(self):
        # Setup retry logic for restful web http requests
        super().__init__()
        jitter_retry = Retry(
            total=5,
            backoff_factor=0.1,
            backoff_jitter=1.25,
            status_forcelist=[400, 403, 404, 500, 502, 503, 504],
            raise_on_status=False,
        )
        self.mount("http://", HTTPAdapter(max_retries=jitter_retry))
        self.mount("https://", HTTPAdapter(max_retries=jitter_retry))


# Module Documentation

## Classes

### Client
- **Description**: Base class for all client implementations.

### OpenAIClient(Client)
- **Description**: A thin wrapper around the OpenAI client, providing methods to interact with OpenAI's API.
- **Constructor**:  
  - `__init__(model: str | None = None, temperature: float | None = None)`: Initializes the OpenAI client with the specified model and temperature. Retrieves the API key from environment variables.

- **Methods**:  
  - `complete(messages: list[dict[str, str]], message_format: type[Message] | dict = TextMessage, temperature: float | None = None, **kwargs) -> ChatCompletion`:  
    - **Description**: Sends a completion request to the OpenAI API with the provided messages and parameters. Retries on RateLimitError.
    - **Parameters**:  
      - `messages`: A list of message dictionaries to send to the API.
      - `message_format`: The format of the response, either a Pydantic model or a dictionary.
      - `temperature`: The sampling temperature to use for the response.
      - `**kwargs`: Additional parameters to pass to the API.
    - **Returns**: A ChatCompletion object containing the response from the OpenAI API.

  - `model_to_schema(model: type[PydanticModel]) -> dict[str, str | dict]`:  
    - **Description**: Converts a Pydantic model into a JSON schema format for OpenAI.
    - **Parameters**:  
      - `model`: The Pydantic model to convert.
    - **Returns**: A dictionary representing the JSON schema of the model.

### CLIClient(Client)
- **Description**: A client for command-line interface operations.
- **Methods**:  
  - `emit(content: Any)`:  
    - **Description**: Prints the content to the console if the environment is not production.
    - **Parameters**:  
      - `content`: The content to print.

### HTTPClient(Client, requests.Session)
- **Description**: A client for making HTTP requests with retry logic.
- **Constructor**:  
  - `__init__()`: Initializes the HTTP client and sets up retry logic for HTTP requests.

- **Details**:  
  - Uses `requests.Session` to manage connections and sessions.
  - Implements a jitter retry strategy for handling transient HTTP errors, retrying on specific status codes.