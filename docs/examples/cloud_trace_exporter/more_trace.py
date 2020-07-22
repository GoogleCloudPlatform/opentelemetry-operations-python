from opentelemetry import trace
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleExportSpanProcessor
from opentelemetry.trace import Link

trace.set_tracer_provider(TracerProvider())

cloud_trace_exporter = CloudTraceSpanExporter()
trace.get_tracer_provider().add_span_processor(
    SimpleExportSpanProcessor(cloud_trace_exporter)
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
    with tracer.start_as_current_span(
        "span_with_link", links=[Link(link_target.context)]
    ):
        pass
    with tracer.start_as_current_span(
        "span_with_link_and_attributes",
        links=[Link(link_target.context, attributes={"link_attr": "string"})],
    ):
        pass

# You can also do a combination of these
with tracer.start_as_current_span(
    "foo_with_event_and_attributes"
) as current_span:
    current_span.add_event(name="event_name", attributes={"event_attr1": 123})
    current_span.set_attribute("bool_attribute", False)
