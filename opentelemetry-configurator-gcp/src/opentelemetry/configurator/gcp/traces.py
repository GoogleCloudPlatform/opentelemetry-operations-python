"""Provides a mechanism to configure the Traces Exporter for GCP."""
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def configure_traces_exporter(resource=None):
    """Configures the Open Telemetry tracing libraries to write to Cloud Trace.

    Args:
      - resource: The resource to include when writing trace data. 

    Effects:

      Calls the 'set_tracer_provider' operation with a TracerProvider that
      will cause traces to be written to the Cloud Trace backend.
    """
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(CloudTraceSpanExporter()))
    trace.set_tracer_provider(provider)
