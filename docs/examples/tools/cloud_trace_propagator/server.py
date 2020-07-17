import opentelemetry.ext.requests
from flask import Flask
from opentelemetry import trace
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.exporter.cloud_trace.cloud_trace_propagator import (
    CloudTraceFormatPropagator,
)
from opentelemetry.ext.flask import FlaskInstrumentor
from opentelemetry.propagators import set_global_httptextformat
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleExportSpanProcessor

# Instrumenting requests
opentelemetry.ext.requests.RequestsInstrumentor().instrument()

# Instrumenting flask
app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)

# Tracer boilerplate
trace.set_tracer_provider(TracerProvider())
trace.get_tracer_provider().add_span_processor(
    SimpleExportSpanProcessor(CloudTraceSpanExporter())
)

# Using the X-Cloud-Trace-Context header
set_global_httptextformat(CloudTraceFormatPropagator())


@app.route("/")
def hello_world():
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("server_span"):
        return "Hello World!"


if __name__ == "__main__":
    port = 5000
    app.run(port=port)
