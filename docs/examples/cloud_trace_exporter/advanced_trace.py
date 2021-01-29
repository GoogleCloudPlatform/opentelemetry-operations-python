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

from opentelemetry import trace
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchExportSpanProcessor
from opentelemetry.trace import Link

trace.set_tracer_provider(TracerProvider())

cloud_trace_exporter = CloudTraceSpanExporter()
trace.get_tracer_provider().add_span_processor(
    # BatchExportSpanProcessor buffers spans and sends them in batches in a
    # background thread.
    BatchExportSpanProcessor(cloud_trace_exporter)
)
tracer = trace.get_tracer(__name__)

# Adding attributes to spans
with tracer.start_as_current_span("foo_with_attribute") as current_span:
    current_span.set_attribute("string_attribute", "str")
    current_span.set_attribute("bool_attribute", False)
    current_span.set_attribute("int_attribute", 3)
    current_span.set_attribute("float_attribute", 3.14)

# Adding events to spans
with tracer.start_as_current_span("foo_with_event") as current_span:
    current_span.add_event(name="event_name",)

# Adding links to spans
with tracer.start_as_current_span("link_target") as link_target:
    # Creates a span "span_with_link" and a link from
    # "span_with_link" -> "link_target"
    with tracer.start_as_current_span(
        "span_with_link", links=[Link(link_target.context)]
    ):
        pass
    # Creates a span "span_with_link" and a link from
    # "span_with_link" -> "link_target". This link also has the attribute
    # {"link_attr": "string"}
    with tracer.start_as_current_span(
        "span_with_link_and_link_attributes",
        links=[Link(link_target.context, attributes={"link_attr": "string"})],
    ):
        pass

# You can also do a combination of these
with tracer.start_as_current_span(
    "foo_with_event_and_attributes"
) as current_span:
    current_span.add_event(name="event_name", attributes={"event_attr1": 123})
    current_span.set_attribute("bool_attribute", False)
