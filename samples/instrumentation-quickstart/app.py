# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from random import randint, uniform
import time

import logging
from pythonjsonlogger import jsonlogger
from opentelemetry.instrumentation.logging import LoggingInstrumentor

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

import requests
from opentelemetry.instrumentation.requests import RequestsInstrumentor

from flask import Flask, url_for
from opentelemetry.instrumentation.flask import FlaskInstrumentor

LoggingInstrumentor().instrument()

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(
    "%(asctime)s %(levelname)s %(message)s %(otelTraceID)s %(otelSpanID)s %(otelTraceSampled)s",
    rename_fields={
        "levelname": "severity",
        "asctime": "timestamp",
        "otelTraceID": "logging.googleapis.com/trace",
        "otelSpanID": "logging.googleapis.com/spanId",
        "otelTraceSampled": "logging.googleapis.com/trace_sampled",
        },
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
# disable logging from Flask until we use Gunicorn
logging.getLogger('werkzeug').setLevel(logging.ERROR)

traceProvider = TracerProvider()
processor = BatchSpanProcessor(OTLPSpanExporter())
traceProvider.add_span_processor(processor)
trace.set_tracer_provider(traceProvider)

reader = PeriodicExportingMetricReader(
    OTLPMetricExporter()
)
meterProvider = MeterProvider(metric_readers=[reader])
metrics.set_meter_provider(meterProvider)

app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()

@app.route('/multi')
def multi():
    subRequests = randint(3, 7)
    logger.info("handle /multi request", extra={'subRequests': subRequests})
    for _ in range(subRequests):
        requests.get(url_for('single', _external=True))
    return 'ok'

@app.route('/single')
def single():
    duration = uniform(0.1, 0.2)
    time.sleep(duration)
    return f'slept {duration} seconds'
