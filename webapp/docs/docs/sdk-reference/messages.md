Last Updated: 2024-11-18 18:33:48 UTC
Lines Changed: +18, -0

# Messages

Messages are a format for structured outputs from OpenAI completions. Outputs are validated against the Message format, guaranteeing the syntax.

Define your own message format by subclassing the Message class, and defining fields.

```python
from concrete.models.messages import Message

class CustomMessage(Message):
    field1: data_type = Field(..., description="Field 1 description")
    field2: data_type = Field(..., description="Field 2 description")
```

Messages can be used in Operators by passing the `response_format` option to string returning functions. By default, the `TextMessage` format is used.
