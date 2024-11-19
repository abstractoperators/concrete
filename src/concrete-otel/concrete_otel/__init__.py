from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

import concrete

# Set up TracerProvider
trace.set_tracer_provider(TracerProvider())

# Configure a ConsoleSpanExporter to visualize spans
span_processor = SimpleSpanProcessor(ConsoleSpanExporter())
trace.get_tracer_provider().add_span_processor(span_processor)

tracer = trace.get_tracer(__name__)


original_function = concrete.operators.Operator.chat


# Patch the function
def patched_function(*args, **kwargs):
    with tracer.start_as_current_span("concrete.Operators.chat") as span:
        span.set_attribute("args", str(args))
        span.set_attribute("kwargs", str(kwargs))
        result = original_function(*args, **kwargs)
        span.set_attribute("result", str(result))
        return result


concrete.operators.Operator.chat = patched_function

# Test the patched function
operator = concrete.operators.Operator()

# Simulate a call to the patched method
with tracer.start_as_current_span("test_call_to_chat") as span:
    result = operator.chat("test_arg")
    print(f"Chat Result: {result}")
    print(f"Span Context: Trace ID: {span.context.trace_id}, Span ID: {span.context.span_id}")
