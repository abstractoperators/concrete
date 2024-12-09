import os
import re
from typing import TYPE_CHECKING

import tiktoken

try:
    from openai import OpenAI  # noqa
    from tiktoken import encoding_for_model
except ImportError as e:
    raise ImportError("Install extra openai to use OpenAIClient. (e.g. `pip install concrete-core[openai]`") from e

from concrete.clients import CLIClient, LMClient
from concrete.models.messages import Message, TextMessage

if TYPE_CHECKING:
    from openai.types.chat import ChatCompletion


class OpenAIClient(LMClient):
    """
    Thin wrapper around open AI client.
    """

    def __init__(self, model: str | None = None, temperature: float | None = None):
        OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.default_temperature = temperature if temperature is not None else float(os.getenv("OPENAI_TEMPERATURE", 0))
        self.model = model or "gpt-4o-mini"

    def message_fits(self, message: str) -> bool:
        """
        Check if the message fits in the model.
        No API for checking - so this is copied manually from https://platform.openai.com/docs/models/gp
        """
        encoding = encoding_for_model(self.model)
        num_tokens = len(encoding.encode(message))

        # Note: No support for -latest models.
        # Also, wtf? Why are the model names so inconsistent?
        gpt_4o_pattern = r"(^gpt-4o$)|(^gpt-4o-\d{4}-\d{2}-\d{2}$)"
        gpt_4o_mini_pattern = r"(^gpt-4o-mini$)|(^gpt-4o-mini-\d{4}-\d{2}-\d{2}$)"
        gpt_o1_preview_pattern = r"(^o1-preview$)|(^o1-preview-\d{4}-\d{2}-\d{2}$)"
        gpt_o1_mini_pattern = r"(^o1-mini$)|(^o1-mini-\d{4}-\d{2}-\d{2}$)"
        gpt_4_turbo_pattern = (
            r"(^gpt-4-turbo$)|(^gpt-4-turbo-\d{4}-\d{2}-\d{2}$)|(^gpt-4-turbo-preview$)|(^gpt-4-\d{4}-preview$)"
        )
        gpt_4_pattern = r"(^gpt-4$)|(^gpt-4-\d{4})"
        gpt_3_5_turbo_pattern = r"(^gpt-3.5-turbo$)|(^gpt-3.5-turbo-\d{4}$)|(^gpt-3.5-turbo-instruct$)"

        if re.search(gpt_4o_pattern, self.model):
            context_window, max_output = 128_000, 16_384
            # Older models have 4k max output, but it seems all the later ones have 16k
        elif re.search(gpt_4o_mini_pattern, self.model):
            context_window, max_output = 128_000, 16_384
        elif re.search(gpt_o1_preview_pattern, self.model):
            context_window, max_output = 128_000, 32_768
        elif re.search(gpt_o1_mini_pattern, self.model):
            context_window, max_output = 128_000, 32_768
        elif re.search(gpt_4_turbo_pattern, self.model):
            context_window, max_output = 128_000, 4_096
        elif re.search(gpt_4_pattern, self.model):
            context_window, max_output = 8_192, 8_192
        elif re.search(gpt_3_5_turbo_pattern, self.model):
            context_window, max_output = 16_384, 4_096

        encoding = tiktoken.encoding_for_model(self.model)
        num_tokens = len(encoding.encode(message))
        return (context_window - max_output) >= num_tokens

    def complete(
        self,
        messages: list[dict[str, str]],
        message_format: type[Message] = TextMessage,
        temperature: float | None = None,
        **kwargs,
    ) -> "ChatCompletion":

        # TODO: Custom tokens_per_message and tokens_per_name
        # https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb
        if not self.message_fits(' '.join([m['content'] for m in messages])):
            raise ValueError("Message does not fit in model")
        from openai import RateLimitError

        request_params = {
            "messages": messages,
            "model": self.model,
            "temperature": (temperature if temperature is not None else self.default_temperature),
            "response_format": message_format,
            **kwargs,
        }

        try:
            if isinstance(message_format, type(Message)):
                # Turn Message into a json_schema
                # https://platform.openai.com/docs/guides/structured-outputs/supported-schemas

                return self.client.beta.chat.completions.parse(**request_params)
            return self.client.chat.completions.create(**request_params)
        except RateLimitError as e:
            CLIClient.emit(f"Rate limit error: {e}")
            raise e  # retry decorator
