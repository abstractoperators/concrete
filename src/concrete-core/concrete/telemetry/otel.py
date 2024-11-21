import os

from concrete.clients import CLIClient

try:
    from functools import wraps

    from opentelemetry import trace
    from opentelemetry.sdk.trace import ConcurrentMultiSpanProcessor, TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor

    from .exporter import FileSpanExporter

    # Set up TracerProvider ~ Tracer Factory
    multi_span_processor = ConcurrentMultiSpanProcessor(num_threads=1)
    span_processor = SimpleSpanProcessor(FileSpanExporter(filepath="trace.log"))
    multi_span_processor.add_span_processor(span_processor)
    trace.set_tracer_provider(TracerProvider(active_span_processor=multi_span_processor))

    def add_tracing(func):
        """Decorator to add OpenTelemetry tracing."""

        tracer = trace.get_tracer(func.__module__)

        @wraps(func)
        def wrapped(self, *args, **kwargs):
            if not os.getenv("TRACE_ENABLED").lower() == 'true':
                return func(self, *args, **kwargs)

            with tracer.start_as_current_span(f"{self.__class__.__name__}.{func.__name__}") as span:
                span.set_attribute("args", str(args))
                span.set_attribute("kwargs", str(kwargs))

                # TODO Make generic to non-AbstractOperator methods
                span.set_attribute('project_id', str(self.project_id))
                span.set_attribute('operator_id', str(self.operator_id))
                span.set_attribute('starting_prompt', str(self.starting_prompt))

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

    def add_tracing(func):
        return func

    CLIClient.emit("concrete[otel] extra dependencies not installed. Tracing is disabled")
