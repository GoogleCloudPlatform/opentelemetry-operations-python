from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def configure_traces_exporter(resource=None):
   provider = TracerProvider(resource=resource)
   provider.add_span_processor(BatchSpanProcessor(CloudTraceSpanExporter()))
   trace.set_tracer_provider(provider)
