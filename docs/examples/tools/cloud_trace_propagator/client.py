import opentelemetry.ext.requests
import requests
from opentelemetry import trace
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.exporter.cloud_trace.cloud_trace_propagator import (
    CloudTraceFormatPropagator,
)
from opentelemetry.propagators import set_global_httptextformat
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleExportSpanProcessor

# Instrumenting requests
opentelemetry.ext.requests.RequestsInstrumentor().instrument()

# Tracer boilerplate
trace.set_tracer_provider(TracerProvider())
trace.get_tracer_provider().add_span_processor(
    SimpleExportSpanProcessor(CloudTraceSpanExporter())
)

# Using the X-Cloud-Trace-Context header
set_global_httptextformat(CloudTraceFormatPropagator())

tracer = trace.get_tracer(__name__)
with tracer.start_as_current_span("client_span"):
    response = requests.get("http://localhost:5000/")
