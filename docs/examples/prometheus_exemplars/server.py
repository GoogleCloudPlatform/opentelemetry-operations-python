#!/usr/bin/env python3
# Copyright 2023 The OpenTelemetry Authors
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

# [START opentelemetry_prom_exemplars_import]

import time
import random
from typing import Dict, Optional

from flask import Flask
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from prometheus_client import make_wsgi_app, Histogram

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBasedTraceIdRatio

# [END opentelemetry_prom_exemplars_import]

# [START opentelemetry_prom_exemplars_setup_exporter]

resource = Resource.create(
    {
        "service.name": "prometheus_exemplars",
        "service.namespace": "examples",
        "service.instance.id": "instance123",
    }
)

tracer_provider = TracerProvider(
    resource=resource,
    # Only sample 1 in 100 requests
    sampler=ParentBasedTraceIdRatio(1 / 100),
)
tracer_provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint="http://otel-collector:4317"))
)

trace.set_tracer_provider(tracer_provider)

tracer = trace.get_tracer(__name__)

# [END opentelemetry_prom_exemplars_setup_exporter]

# [START opentelemetry_prom_exemplars_instrument]

app = Flask(__name__)
# Add prometheus wsgi middleware to route /metrics requests
app.wsgi_app = DispatcherMiddleware(
    app.wsgi_app, {"/metrics": make_wsgi_app()}
)

FlaskInstrumentor().instrument_app(app)

hist = Histogram(
    "my_prom_hist",
    "Times requests with prometheus and exemplars",
    ("name",),
    unit="s",
)


@app.route("/")
def hello_world():
    # unfortunately, Histogram.time()'s returned Timer doesn't let you set the exemplar.
    # Instead, time it manually.
    start = time.time_ns()

    with tracer.start_as_current_span("do_work"):
        time.sleep(random.paretovariate(0.75) / 100)

    end = time.time_ns()
    duration_sec = (end - start) / 10**9

    # observe with exemplars
    # [START opentelemetry_prom_exemplars_observe]
    hist.labels(name="foo").observe(duration_sec, get_prom_exemplars())
    # [END opentelemetry_prom_exemplars_observe]

    return "Hello, World!"


# [END opentelemetry_prom_exemplars_instrument]


# [START opentelemetry_prom_exemplars_attach]
def get_prom_exemplars() -> Optional[Dict[str, str]]:
    """Generates an exemplar dictionary from the current implicit OTel context if available"""
    span_context = trace.get_current_span().get_span_context()

    # Only include the exemplar if it is valid and sampled
    if span_context.is_valid and span_context.trace_flags.sampled:
        # You must set the trace_id and span_id exemplar labels like this to link OTel and
        # Prometheus. They must be formatted as hexadecimal strings.
        return {
            "trace_id": trace.format_trace_id(span_context.trace_id),
            "span_id": trace.format_span_id(span_context.span_id),
        }

    return None
    # [END opentelemetry_prom_exemplars_attach]
