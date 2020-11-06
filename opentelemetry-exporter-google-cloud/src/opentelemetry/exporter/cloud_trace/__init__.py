# Copyright OpenTelemetry Authors
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

"""Cloud Trace Span Exporter for OpenTelemetry. Uses Cloud Trace Client's REST
API to export traces and spans for viewing in Cloud Trace.

Usage
-----

.. code-block:: python

    from opentelemetry import trace
    from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
    from opentelemetry.sdk.trace import TracerProvider

    # For debugging
    from opentelemetry.sdk.trace.export import SimpleExportSpanProcessor
    # Otherwise
    from opentelemetry.sdk.trace.export import BatchExportSpanProcessor

    trace.set_tracer_provider(TracerProvider())

    cloud_trace_exporter = CloudTraceSpanExporter()
    trace.get_tracer_provider().add_span_processor(
        BatchExportSpanProcessor(cloud_trace_exporter)
    )
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("foo"):
        print("Hello world!")


When not debugging, make sure to use
:class:`opentelemetry.sdk.trace.export.BatchExportSpanProcessor` with the
default parameters for performance reasons.

API
---
"""

import collections
import logging
from typing import Any, Dict, List, Optional, Sequence, Tuple

import google.auth
import opentelemetry.trace as trace_api
import pkg_resources
from google.cloud.trace_v2 import TraceServiceClient
from google.cloud.trace_v2.proto.trace_pb2 import AttributeValue
from google.cloud.trace_v2.proto.trace_pb2 import Span as ProtoSpan
from google.cloud.trace_v2.proto.trace_pb2 import TruncatableString
from google.protobuf.timestamp_pb2 import Timestamp
from google.rpc.status_pb2 import Status
from opentelemetry.exporter.google.version import (
    __version__ as google_ext_version,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import Event
from opentelemetry.sdk.trace.export import Span, SpanExporter, SpanExportResult
from opentelemetry.sdk.util import BoundedDict
from opentelemetry.trace.span import (
    get_hexadecimal_span_id,
    get_hexadecimal_trace_id,
)
from opentelemetry.util import types

logger = logging.getLogger(__name__)

MAX_NUM_LINKS = 128
MAX_NUM_EVENTS = 32
MAX_EVENT_ATTRS = 4
MAX_LINK_ATTRS = 32
MAX_SPAN_ATTRS = 32


class CloudTraceSpanExporter(SpanExporter):
    """Cloud Trace span exporter for OpenTelemetry.

    Args:
        project_id: ID of the cloud project that will receive the traces.
        client: Cloud Trace client. If not given, will be taken from gcloud
            default credentials
    """

    def __init__(
        self, project_id=None, client=None,
    ):
        self.client = client or TraceServiceClient()
        if not project_id:
            _, self.project_id = google.auth.default()
        else:
            self.project_id = project_id

    def export(self, spans: Sequence[Span]) -> SpanExportResult:
        """Export the spans to Cloud Trace.

        See: https://cloud.google.com/trace/docs/reference/v2/rest/v2/projects.traces/batchWrite

        Args:
            spans: Sequence of spans to export
        """
        try:
            self.client.batch_write_spans(
                "projects/{}".format(self.project_id),
                self._translate_to_cloud_trace(spans),
            )
        # pylint: disable=broad-except
        except Exception as ex:
            logger.error("Error while writing to Cloud Trace", exc_info=ex)
            return SpanExportResult.FAILURE

        return SpanExportResult.SUCCESS

    def _translate_to_cloud_trace(
        self, spans: Sequence[Span]
    ) -> List[Dict[str, Any]]:
        """Translate the spans to Cloud Trace format.

        Args:
            spans: Sequence of spans to convert
        """

        cloud_trace_spans = []

        for span in spans:
            ctx = span.get_span_context()
            trace_id = get_hexadecimal_trace_id(ctx.trace_id)
            span_id = get_hexadecimal_span_id(ctx.span_id)
            span_name = "projects/{}/traces/{}/spans/{}".format(
                self.project_id, trace_id, span_id
            )

            parent_id = None
            if span.parent:
                parent_id = get_hexadecimal_span_id(span.parent.span_id)

            start_time = _get_time_from_ns(span.start_time)
            end_time = _get_time_from_ns(span.end_time)

            if len(span.attributes) > MAX_SPAN_ATTRS:
                logger.warning(
                    "Span has more then %s attributes, some will be truncated",
                    MAX_SPAN_ATTRS,
                )

            # Span does not support a MonitoredResource object. We put the
            # information into attributes instead.
            resources_and_attrs = _extract_resources(span.resource)
            resources_and_attrs.update(span.attributes)

            cloud_trace_spans.append(
                {
                    "name": span_name,
                    "span_id": span_id,
                    "display_name": _get_truncatable_str_object(
                        span.name, 128
                    ),
                    "start_time": start_time,
                    "end_time": end_time,
                    "parent_span_id": parent_id,
                    "attributes": _extract_attributes(
                        resources_and_attrs,
                        MAX_SPAN_ATTRS,
                        add_agent_attr=True,
                    ),
                    "links": _extract_links(span.links),  # type: ignore[has-type]
                    "status": _extract_status(span.status),  # type: ignore[arg-type]
                    "time_events": _extract_events(span.events),
                    "span_kind": _extract_span_kind(span.kind),
                }
            )
            # TODO: Leverage more of the Cloud Trace API, e.g.
            #  same_process_as_parent_span and child_span_count

        return cloud_trace_spans

    def shutdown(self):
        pass


def _get_time_from_ns(nanoseconds: int) -> Optional[Timestamp]:
    """Given epoch nanoseconds, split into epoch milliseconds and remaining
    nanoseconds"""
    if not nanoseconds:
        return None
    ts = Timestamp()
    # pylint: disable=no-member
    ts.FromNanoseconds(nanoseconds)
    return ts


def _get_truncatable_str_object(str_to_convert: str, max_length: int):
    """Truncate the string if it exceeds the length limit and record the
    truncated bytes count."""
    truncated, truncated_byte_count = _truncate_str(str_to_convert, max_length)

    return TruncatableString(
        value=truncated, truncated_byte_count=truncated_byte_count
    )


def _truncate_str(str_to_check: str, limit: int) -> Tuple[str, int]:
    """Check the length of a string. If exceeds limit, then truncate it."""
    encoded = str_to_check.encode("utf-8")
    truncated_str = encoded[:limit].decode("utf-8", errors="ignore")
    return truncated_str, len(encoded) - len(truncated_str.encode("utf-8"))


def _extract_status(status: trace_api.Status) -> Optional[Status]:
    """Convert a Status object to protobuf object."""
    if not status:
        return None
    status_dict = {"details": None, "code": status.status_code.value}

    if status.description is not None:
        status_dict["message"] = status.description

    return Status(**status_dict)


def _extract_links(links: Sequence[trace_api.Link]) -> ProtoSpan.Links:
    """Convert span.links"""
    if not links:
        return None
    extracted_links = []
    dropped_links = 0
    if len(links) > MAX_NUM_LINKS:
        logger.warning(
            "Exporting more then %s links, some will be truncated",
            MAX_NUM_LINKS,
        )
        dropped_links = len(links) - MAX_NUM_LINKS
        links = links[:MAX_NUM_LINKS]
    for link in links:
        link_attributes = link.attributes or {}
        if len(link_attributes) > MAX_LINK_ATTRS:
            logger.warning(
                "Link has more then %s attributes, some will be truncated",
                MAX_LINK_ATTRS,
            )
        trace_id = get_hexadecimal_trace_id(link.context.trace_id)
        span_id = get_hexadecimal_span_id(link.context.span_id)
        extracted_links.append(
            {
                "trace_id": trace_id,
                "span_id": span_id,
                "type": "TYPE_UNSPECIFIED",
                "attributes": _extract_attributes(
                    link_attributes, MAX_LINK_ATTRS
                ),
            }
        )
    return ProtoSpan.Links(
        link=extracted_links, dropped_links_count=dropped_links
    )


def _extract_events(events: Sequence[Event]) -> ProtoSpan.TimeEvents:
    """Convert span.events to dict."""
    if not events:
        return None
    logs = []
    dropped_annontations = 0
    if len(events) > MAX_NUM_EVENTS:
        logger.warning(
            "Exporting more then %s annotations, some will be truncated",
            MAX_NUM_EVENTS,
        )
        dropped_annontations = len(events) - MAX_NUM_EVENTS
        events = events[:MAX_NUM_EVENTS]
    for event in events:
        if event.attributes and len(event.attributes) > MAX_EVENT_ATTRS:
            logger.warning(
                "Event %s has more then %s attributes, some will be truncated",
                event.name,
                MAX_EVENT_ATTRS,
            )
        logs.append(
            {
                "time": _get_time_from_ns(event.timestamp),
                "annotation": {
                    "description": _get_truncatable_str_object(
                        event.name, 256
                    ),
                    "attributes": _extract_attributes(
                        event.attributes, MAX_EVENT_ATTRS
                    ),
                },
            }
        )
    return ProtoSpan.TimeEvents(
        time_event=logs,
        dropped_annotations_count=dropped_annontations,
        dropped_message_events_count=0,
    )


# pylint: disable=no-member
SPAN_KIND_MAPPING = {
    trace_api.SpanKind.INTERNAL: ProtoSpan.SpanKind.INTERNAL,
    trace_api.SpanKind.CLIENT: ProtoSpan.SpanKind.CLIENT,
    trace_api.SpanKind.SERVER: ProtoSpan.SpanKind.SERVER,
    trace_api.SpanKind.PRODUCER: ProtoSpan.SpanKind.PRODUCER,
    trace_api.SpanKind.CONSUMER: ProtoSpan.SpanKind.CONSUMER,
}


# pylint: disable=no-member
def _extract_span_kind(span_kind: trace_api.SpanKind) -> ProtoSpan.SpanKind:
    return SPAN_KIND_MAPPING.get(
        span_kind, ProtoSpan.SpanKind.SPAN_KIND_UNSPECIFIED
    )


def _strip_characters(ot_version):
    return "".join(filter(lambda x: x.isdigit() or x == ".", ot_version))


OT_RESOURCE_ATTRIBUTE_TO_GCP = {
    "gce_instance": {
        "host.id": "instance_id",
        "cloud.account.id": "project_id",
        "cloud.zone": "zone",
    },
    "gke_container": {
        "k8s.cluster.name": "cluster_name",
        "k8s.namespace.name": "namespace_id",
        "k8s.pod.name": "pod_id",
        "host.id": "instance_id",
        "container.name": "container_name",
        "cloud.account.id": "project_id",
        "cloud.zone": "zone",
    },
}


def _extract_resources(resource: Resource) -> Dict[str, str]:
    resource_attributes = resource.attributes
    if resource_attributes.get("cloud.provider") != "gcp":
        return {}
    resource_type = resource_attributes["gcp.resource_type"]
    if (
        not isinstance(resource_type, str)
        or resource_type not in OT_RESOURCE_ATTRIBUTE_TO_GCP
    ):
        return {}
    return {
        "g.co/r/{}/{}".format(resource_type, gcp_resource_key,): str(
            resource_attributes[ot_resource_key]
        )
        for ot_resource_key, gcp_resource_key in OT_RESOURCE_ATTRIBUTE_TO_GCP[
            resource_type
        ].items()
    }


LABELS_MAPPING = {
    # this one might be http.flavor? I'm not sure
    "http.scheme": "/http/client_protocol",
    "http.host": "/http/host",
    "http.method": "/http/method",
    # https://github.com/open-telemetry/opentelemetry-specification/blob/master/specification/trace/semantic_conventions/http.md#common-attributes
    "http.request_content_length": "/http/request/size",
    "http.response_content_length": "/http/response/size",
    "http.route": "/http/route",
    "http.status_code": "/http/status_code",
    "http.url": "/http/url",
    "http.user_agent": "/http/user_agent",
}


def _extract_attributes(
    attrs: types.Attributes,
    num_attrs_limit: int,
    add_agent_attr: bool = False,
) -> ProtoSpan.Attributes:
    """Convert span.attributes to dict."""
    attributes_dict = BoundedDict(num_attrs_limit)
    invalid_value_dropped_count = 0
    for key, value in attrs.items() if attrs else []:
        key = _truncate_str(key, 128)[0]
        if key in LABELS_MAPPING:  # pylint: disable=consider-using-get
            key = LABELS_MAPPING[key]
        value = _format_attribute_value(value)

        if value:
            attributes_dict[key] = value
        else:
            invalid_value_dropped_count += 1
    if add_agent_attr:
        attributes_dict["g.co/agent"] = _format_attribute_value(
            "opentelemetry-python {}; google-cloud-trace-exporter {}".format(
                _strip_characters(
                    pkg_resources.get_distribution("opentelemetry-sdk").version
                ),
                _strip_characters(google_ext_version),
            )
        )
    return ProtoSpan.Attributes(
        attribute_map=attributes_dict,
        dropped_attributes_count=attributes_dict.dropped
        + invalid_value_dropped_count,
    )


def _format_attribute_value(value: types.AttributeValue) -> AttributeValue:
    if isinstance(value, bool):
        value_type = "bool_value"
    elif isinstance(value, int):
        value_type = "int_value"
    elif isinstance(value, str):
        value_type = "string_value"
        value = _get_truncatable_str_object(value, 256)
    elif isinstance(value, float):
        value_type = "string_value"
        value = _get_truncatable_str_object("{:0.4f}".format(value), 256)
    elif isinstance(value, collections.Sequence):
        value_type = "string_value"
        value = _get_truncatable_str_object(
            ",".join(str(x) for x in value), 256
        )
    else:
        logger.warning(
            "ignoring attribute value %s of type %s. Values type must be one "
            "of bool, int, string or float, or a sequence of these",
            value,
            type(value),
        )
        return None

    return AttributeValue(**{value_type: value})
