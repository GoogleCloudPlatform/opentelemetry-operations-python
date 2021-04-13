# Copyright 2021 Google
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

import random
import time

# [START opentelemetry_trace_import]

from opentelemetry import trace
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Link

# [END opentelemetry_trace_import]

# [START opentelemetry_foobar]
print("Hello test")
# [END opentelemetry_foobar]

# [START opentelemetry_setup_exporter]

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

# [END opentelemetry_setup_exporter]


def do_work() -> None:
    time.sleep(random.random() * 0.5)


# [START opentelemetry_trace_custom_span]

with tracer.start_span("foo_with_attribute") as current_span:
    do_work()

    # Add attributes to the spans of various types
    current_span.set_attribute("string_attribute", "str")
    current_span.set_attribute("bool_attribute", False)
    current_span.set_attribute("int_attribute", 3)
    current_span.set_attribute("float_attribute", 3.14)

# [END opentelemetry_trace_custom_span]

# [START opentelemetry_trace_custom_span_events]

# Adding events to spans
with tracer.start_as_current_span("foo_with_event") as current_span:
    do_work()
    current_span.add_event(name="event_name")

# [END opentelemetry_trace_custom_span_events]

# [START opentelemetry_trace_custom_span_links]

# Adding links to spans
with tracer.start_as_current_span("link_target") as link_target:
    # Using start_as_current_span() instead of start_span() will make spans
    # created within this scope children of foo_with_attribute

    # Creates a span "span_with_link" and a link from
    # "span_with_link" -> "link_target"
    with tracer.start_as_current_span(
        "span_with_link", links=[Link(link_target.context)]
    ):
        do_work()

    # Creates a span "span_with_link" and a link from
    # "span_with_link" -> "link_target". This link also has the attribute
    # {"link_attr": "string"}
    with tracer.start_as_current_span(
        "span_with_link_and_link_attributes",
        links=[Link(link_target.context, attributes={"link_attr": "string"})],
    ):
        do_work()

# [END opentelemetry_trace_custom_span_links]
