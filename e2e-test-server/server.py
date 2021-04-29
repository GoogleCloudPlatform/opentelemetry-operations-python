import contextlib
import os
from typing import Iterator

from flask import Flask, Response, request
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ALWAYS_ON
from opentelemetry.trace import Tracer

TEST_ID = "test-id"
INSTRUMENTING_MODULE_NAME = "opentelemetry-ops-e2e-test-server"

app = Flask(__name__)


@contextlib.contextmanager
def common_setup() -> Iterator[tuple[str, Tracer]]:
    """\
    Context manager with common setup for test endpoints

    It extracts the test-id header, creates a tracer, and finally flushes
    spans created during the test
    """

    if TEST_ID not in request.headers:
        raise Exception(f"{TEST_ID} header is required")
    test_id = request.headers[TEST_ID]

    tracer_provider = TracerProvider(
        sampler=ALWAYS_ON,
        active_span_processor=BatchSpanProcessor(
            CloudTraceSpanExporter(project_id=os.environ.get("PROJECT_ID"))
        ),
    )
    tracer = tracer_provider.get_tracer(INSTRUMENTING_MODULE_NAME)

    try:
        yield test_id, tracer
    finally:
        tracer_provider.shutdown()


@app.route("/health")
def health():
    return "OK", 200


@app.route("/basicTrace", methods=["POST"])
def basicTrace():
    """Create a basic trace"""

    with common_setup() as (test_id, tracer):
        with tracer.start_span("basicTrace", attributes={TEST_ID: test_id}):
            pass

    return Response(status=200)
