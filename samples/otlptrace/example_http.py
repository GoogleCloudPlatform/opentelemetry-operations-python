#!/usr/bin/env python3
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

import google.auth
import google.auth.transport.requests
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

credentials, project_id = google.auth.default()
request = google.auth.transport.requests.Request()
credentials.refresh(request)
req_headers = {
    "x-goog-user-project": credentials.quota_project_id,
    "Authorization": "Bearer " + credentials.token,
}
resource = Resource.create(attributes={SERVICE_NAME: "otlp-gcp-http-sample"})

trace_provider = TracerProvider(resource=resource)
processor = BatchSpanProcessor(OTLPSpanExporter(headers=req_headers))
trace_provider.add_span_processor(processor)
trace.set_tracer_provider(trace_provider)
tracer = trace.get_tracer("my.tracer.name")


def do_work():
    with tracer.start_as_current_span("span-http") as span:
        # do some work that 'span' will track
        print("doing some work...")
        # When the 'with' block goes out of scope, 'span' is closed for you


do_work()
