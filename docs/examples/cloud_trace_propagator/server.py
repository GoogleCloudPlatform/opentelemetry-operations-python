#!/usr/bin/env python3
# Copyright 2021 The OpenTelemetry Authors
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

import opentelemetry.ext.requests
from opentelemetry import trace
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.propagators.cloud_trace_propagator import (
    CloudTraceFormatPropagator,
)

from flask import Flask

# Instrumenting requests
opentelemetry.ext.requests.RequestsInstrumentor().instrument()

# Instrumenting flask
app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)

# Tracer boilerplate
trace.set_tracer_provider(TracerProvider())
trace.get_tracer_provider().add_span_processor(
    SimpleSpanProcessor(CloudTraceSpanExporter())
)

# Using the X-Cloud-Trace-Context header
set_global_textmap(CloudTraceFormatPropagator())


@app.route("/")
def hello_world():
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("server_span"):
        return "Hello World!"


if __name__ == "__main__":
    port = 5000
    app.run(port=port)
