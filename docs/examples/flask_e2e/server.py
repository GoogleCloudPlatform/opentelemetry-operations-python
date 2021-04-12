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

# [START opentelemetry_flask_import]

import time

from flask import Flask
from opentelemetry import trace
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.cloud_trace_propagator import (
    CloudTraceFormatPropagator,
)
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# [END opentelemetry_flask_import]

# [START opentelemetry_flask_setup_propagator]

set_global_textmap(CloudTraceFormatPropagator())

# [END opentelemetry_flask_setup_propagator]

# [START opentelemetry_flask_setup_exporter]

tracer_provider = TracerProvider()
cloud_trace_exporter = CloudTraceSpanExporter()
tracer_provider.add_span_processor(
    # BatchSpanProcessor buffers spans and sends them in batches in a
    # background thread. The default parameters are sensible, but can be
    # tweaked to optimize your performance
    BatchSpanProcessor(cloud_trace_exporter)
)
trace.set_tracer_provider(tracer_provider)

tracer = trace.get_tracer(__name__)

# [END opentelemetry_flask_setup_exporter]

# [START opentelemetry_flask_instrument]

app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)


@app.route("/")
def hello_world():
    # You can still use the OpenTelemetry API as usual to create custom spans
    # within your trace
    with tracer.start_as_current_span("do_work"):
        time.sleep(0.1)

    return "Hello, World!"


# [END opentelemetry_flask_instrument]
