import logging
import typing
from os import linesep

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import (
    ConsoleSpanExporter,
    SpanExporter,
    SpanExportResult,
)


class FileSpanExporter(ConsoleSpanExporter):
    """Implementation of SpanExporter that writes spans to a file."""

    def __init__(
        self,
        filepath: str,
        service_name: typing.Optional[str] = None,
        formatter: typing.Callable[[ReadableSpan], str] = lambda span: span.to_json() + linesep,
    ):
        self.filepath = filepath
        super().__init__(
            service_name=service_name,
            formatter=formatter,
        )

    def export(self, spans: typing.Sequence[ReadableSpan]) -> SpanExportResult:
        with open(self.filepath, 'a+', encoding='utf-8') as file:
            self.out = file
            return super().export(spans)


class LogExporter(SpanExporter):
    def __init__(
        self,
        logger: logging.Logger,
    ):
        self.logger = logger
        if not self.logger.hasHandlers():
            raise ValueError("Logger must have at least one handler.")

    def export(self, spans: typing.Sequence[ReadableSpan]) -> SpanExportResult:
        for span in spans:
            span_data = {
                "name": span.name,
                "start_time": span.start_time,
                "end_time": span.end_time,
                "attributes": span.attributes,
            }
            self.logger.info(f"Otel Span Logged: {span_data}")
        return SpanExportResult.SUCCESS
