#!/usr/bin/env python3
# Copyright The OpenTelemetry Authors
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
import requests
from opentelemetry import trace
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.propagators import set_global_textmap
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleExportSpanProcessor
from opentelemetry.tools.cloud_trace_propagator import (
    CloudTraceFormatPropagator,
)

# Instrumenting requests
opentelemetry.ext.requests.RequestsInstrumentor().instrument()

# Tracer boilerplate
trace.set_tracer_provider(TracerProvider())
trace.get_tracer_provider().add_span_processor(
    SimpleExportSpanProcessor(CloudTraceSpanExporter())
)

# Using the X-Cloud-Trace-Context header
set_global_textmap(CloudTraceFormatPropagator())

tracer = trace.get_tracer(__name__)
with tracer.start_as_current_span("client_span"):
    response = requests.get("http://localhost:5000/")
