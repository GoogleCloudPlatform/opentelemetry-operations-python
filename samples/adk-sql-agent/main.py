# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import google.auth
import google.auth.transport.requests
import grpc
from google.auth.transport.grpc import AuthMetadataPlugin
from opentelemetry import _events as events
from opentelemetry import _logs as logs
from opentelemetry import metrics, trace
from opentelemetry.exporter.cloud_logging import CloudLoggingExporter
from opentelemetry.exporter.cloud_monitoring import CloudMonitoringMetricsExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.instrumentation.sqlite3 import SQLite3Instrumentor
from opentelemetry.instrumentation.google_genai import GoogleGenAiSdkInstrumentor
from opentelemetry.instrumentation.vertexai import VertexAIInstrumentor
from opentelemetry.sdk._events import EventLoggerProvider
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
import os

import uvicorn
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app

# Get the directory where main.py is located
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
# Example session DB URL (e.g., SQLite)
SESSION_DB_URL = "sqlite:///./sessions.db"
# Example allowed origins for CORS
ALLOWED_ORIGINS = ["http://localhost", "http://localhost:8080", "*"]
# Set web=True if you intend to serve a web interface, False otherwise
SERVE_WEB_INTERFACE = True

# [START opentelemetry_adk_otel_setup]
def setup_opentelemetry() -> None:
    credentials, project_id = google.auth.default()
    resource = Resource.create(
        attributes={
            SERVICE_NAME: "adk-sql-agent",
            # The project to send spans to
            "gcp.project_id": project_id,
        }
    )

    # Set up OTLP auth
    request = google.auth.transport.requests.Request()
    auth_metadata_plugin = AuthMetadataPlugin(credentials=credentials, request=request)
    channel_creds = grpc.composite_channel_credentials(
        grpc.ssl_channel_credentials(),
        grpc.metadata_call_credentials(auth_metadata_plugin),
    )

    # Set up OpenTelemetry Python SDK
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(
                credentials=channel_creds,
                endpoint="https://telemetry.googleapis.com:443/v1/traces",
            )
        )
    )
    trace.set_tracer_provider(tracer_provider)

    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(
        BatchLogRecordProcessor(CloudLoggingExporter())
    )
    logs.set_logger_provider(logger_provider)

    event_logger_provider = EventLoggerProvider(logger_provider)
    events.set_event_logger_provider(event_logger_provider)

    reader = PeriodicExportingMetricReader(CloudMonitoringMetricsExporter())
    meter_provider = MeterProvider(metric_readers=[reader], resource=resource)
    metrics.set_meter_provider(meter_provider)

    # Load instrumentors
    SQLite3Instrumentor().instrument()
    VertexAIInstrumentor().instrument()
    GoogleGenAiSdkInstrumentor().instrument()


# [END opentelemetry_adk_otel_setup]


def main() -> None:
    # Make sure to set:
    # OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED=true
    # OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true
    # in order to full prompts and responses and logs messages.
    # For this sample, these can be set by loading the `main.env` file.
    setup_opentelemetry()

    # Call the function to get the FastAPI app instance.
    # Ensure that the agent director name is the name of directory containing agent subdirectories,
    # where each subdirectory represents a single agent with __init__.py and agent.py files.
    # For this example this would be the current directory containing main.py.
    # Note: Calling this method attempts to set the global tracer provider, which has already been
    # set by the setup_opentelemetry() function.
    app = get_fast_api_app(
        agents_dir=AGENT_DIR,
        session_service_uri=SESSION_DB_URL,
        allow_origins=ALLOWED_ORIGINS,
        web=SERVE_WEB_INTERFACE,
    )

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))


if __name__ == "__main__":
    main()
