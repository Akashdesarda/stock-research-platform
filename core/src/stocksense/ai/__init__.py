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

    from stocksense.config import get_settings

    settings = get_settings()

    # Set up the tracer provider
    tracer_provider = TracerProvider()
    trace.set_tracer_provider(tracer_provider)

    # Add the OpenInference span processor
    endpoint = (
        f"{settings.common.base_url}:{settings.common.phoenix_port}/v1/traces"
    )

    exporter = OTLPSpanExporter(endpoint=endpoint)

    tracer_provider.add_span_processor(OpenInferenceSpanProcessor())
    tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))
