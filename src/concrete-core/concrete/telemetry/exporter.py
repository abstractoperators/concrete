"""
This module contains a custom file exporter
https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/exporter/fileexporter Is in alpha
"""

import typing
from os import linesep

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import ConsoleSpanExporter


class FileSpanExporter(ConsoleSpanExporter):
    """Implementation of SpanExporter that writes spans to a file.
    Extends ConsoleSpanExporter to inherit its formatting capabilities.

    Notes:
    ConsoleSpanExporter.out: typing.IO can handle file objects
    """

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

    def export(self, spans: typing.Sequence[ReadableSpan]) -> None:
        with open(self.filepath, 'a+', encoding='utf-8') as file:
            self.out = file
            super().export(spans)

    def shutdown(self) -> None:
        self.file.close()
