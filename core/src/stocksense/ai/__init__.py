import json
from contextlib import contextmanager
from typing import Any

from stocksense.config import get_settings

settings = get_settings()


def setup_phoenix_tracing():
    from openinference.instrumentation.pydantic_ai import (
        OpenInferenceSpanProcessor,
    )
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
        OTLPSpanExporter,
    )
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor

    # Set up the tracer provider
    tracer_provider = TracerProvider()
    trace.set_tracer_provider(tracer_provider)

    # Add the OpenInference span processor
    endpoint = f"{settings.common.phoenix_url}:{settings.common.phoenix_port}/v1/traces"

    exporter = OTLPSpanExporter(endpoint=endpoint)

    tracer_provider.add_span_processor(OpenInferenceSpanProcessor())
    tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))


@contextmanager
def track_agent_session(
    name: str,
    session_id: str,
    input_prompt: str,
    metadata: dict[str, Any] | None = None,
):
    """
    Reusable context manager to set up OpenTelemetry and OpenInference tracing
    for an agent session.
    """
    from openinference.instrumentation import using_session
    from openinference.semconv.trace import SpanAttributes
    from opentelemetry import trace

    tracer = trace.get_tracer(__name__)

    attributes = {
        SpanAttributes.OPENINFERENCE_SPAN_KIND: "agent",
        SpanAttributes.SESSION_ID: session_id,
        SpanAttributes.INPUT_VALUE: input_prompt,
    }

    if metadata:
        attributes[SpanAttributes.METADATA] = json.dumps(metadata)

    with tracer.start_as_current_span(name=name, attributes=attributes) as span:
        with using_session(session_id):
            yield span
