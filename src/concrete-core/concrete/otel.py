from .clients import CLIClient

try:
    from functools import wraps

    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

    # Set up TracerProvider ~ Tracer Factory
    span_processor = SimpleSpanProcessor(ConsoleSpanExporter())
    trace.set_tracer_provider(TracerProvider(active_span_processor=span_processor))

    def otel_wrapper(func):
        """Decorator to add OpenTelemetry tracing."""

        tracer = trace.get_tracer(func.__module__)

        @wraps(func)
        def wrapped(self, *args, **kwargs):
            with tracer.start_as_current_span(f"{self.__class__.__name__}.{func.__name__}") as span:
                span.set_attribute("args", str(args))
                span.set_attribute("kwargs", str(kwargs))

                # TODO: Make generic to non-operator.qna
                # span.set_attribute("operator_id", str(self.operator_id))
                # span.set_attribute("project_id", str(self.project_id))
                # Assume a bound method
                # Set all self.attributes as span attribute
                # for k, v in self.__dict__.items():

                try:
                    result = func(self, *args, **kwargs)
                    span.set_attribute("result", str(result))
                    return result
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(trace.status.Status(trace.status.StatusCode.ERROR))
                    raise

        return wrapped

except ImportError:

    def otel_wrapper(func):
        return func

    CLIClient.emit("OpenTelemetry not installed, skipping OpenTelemetry tracing.")
