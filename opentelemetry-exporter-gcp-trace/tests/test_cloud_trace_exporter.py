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

import unittest
from unittest import mock

import pkg_resources
from google.cloud.trace_v2.proto.trace_pb2 import AttributeValue
from google.cloud.trace_v2.proto.trace_pb2 import Span as ProtoSpan
from google.cloud.trace_v2.proto.trace_pb2 import TruncatableString
from google.rpc import code_pb2
from google.rpc.status_pb2 import Status
from opentelemetry.exporter.cloud_trace import (
    MAX_EVENT_ATTRS,
    MAX_LINK_ATTRS,
    MAX_NUM_EVENTS,
    MAX_NUM_LINKS,
    CloudTraceSpanExporter,
    _extract_attributes,
    _extract_events,
    _extract_links,
    _extract_resources,
    _extract_span_kind,
    _extract_status,
    _format_attribute_value,
    _get_time_from_ns,
    _strip_characters,
    _truncate_str,
)
from opentelemetry.exporter.cloud_trace.version import __version__
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import Event
from opentelemetry.sdk.trace import _Span as Span
from opentelemetry.trace import Link, SpanContext, SpanKind
from opentelemetry.trace.status import Status as SpanStatus
from opentelemetry.trace.status import StatusCode


# pylint: disable=too-many-public-methods
class TestCloudTraceSpanExporter(unittest.TestCase):
    def setUp(self):
        self.client_patcher = mock.patch(
            "opentelemetry.exporter.cloud_trace.TraceServiceClient"
        )
        self.client_patcher.start()

    def tearDown(self):
        self.client_patcher.stop()

    @classmethod
    def setUpClass(cls):
        cls.project_id = "PROJECT"
        cls.attributes_variety_pack = {
            "str_key": "str_value",
            "bool_key": False,
            "double_key": 1.421,
            "int_key": 123,
        }
        cls.extracted_attributes_variety_pack = ProtoSpan.Attributes(
            attribute_map={
                "str_key": AttributeValue(
                    string_value=TruncatableString(
                        value="str_value", truncated_byte_count=0
                    )
                ),
                "bool_key": AttributeValue(bool_value=False),
                "double_key": AttributeValue(
                    string_value=TruncatableString(
                        value="1.4210", truncated_byte_count=0
                    )
                ),
                "int_key": AttributeValue(int_value=123),
            }
        )
        cls.agent_code = _format_attribute_value(
            "opentelemetry-python {}; google-cloud-trace-exporter {}".format(
                _strip_characters(
                    pkg_resources.get_distribution("opentelemetry-sdk").version
                ),
                _strip_characters(__version__),
            )
        )
        cls.example_trace_id = "6e0c63257de34c92bf9efcd03927272e"
        cls.example_span_id = "95bb5edabd45950f"
        cls.example_time_in_ns = 1589919268850900051
        cls.example_time_stamp = _get_time_from_ns(cls.example_time_in_ns)
        cls.str_300 = "a" * 300
        cls.str_256 = "a" * 256
        cls.str_128 = "a" * 128

    def test_constructor_default(self):
        exporter = CloudTraceSpanExporter(self.project_id)
        self.assertEqual(exporter.project_id, self.project_id)

    def test_constructor_explicit(self):
        client = mock.Mock()
        exporter = CloudTraceSpanExporter(self.project_id, client=client)

        self.assertIs(exporter.client, client)
        self.assertEqual(exporter.project_id, self.project_id)

    def test_export(self):
        resource_info = Resource(
            {
                "cloud.account.id": 123,
                "host.id": "host",
                "cloud.zone": "US",
                "cloud.provider": "gcp",
                "gcp.resource_type": "gce_instance",
            }
        )
        span_datas = [
            Span(
                name="span_name",
                context=SpanContext(
                    trace_id=int(self.example_trace_id, 16),
                    span_id=int(self.example_span_id, 16),
                    is_remote=False,
                ),
                parent=None,
                kind=SpanKind.INTERNAL,
                resource=resource_info,
                attributes={"attr_key": "attr_value"},
            )
        ]

        cloud_trace_spans = {
            "name": "projects/{}/traces/{}/spans/{}".format(
                self.project_id, self.example_trace_id, self.example_span_id
            ),
            "span_id": self.example_span_id,
            "parent_span_id": None,
            "display_name": TruncatableString(
                value="span_name", truncated_byte_count=0
            ),
            "attributes": ProtoSpan.Attributes(
                attribute_map={
                    "g.co/r/gce_instance/zone": _format_attribute_value("US"),
                    "g.co/r/gce_instance/instance_id": _format_attribute_value(
                        "host"
                    ),
                    "g.co/r/gce_instance/project_id": _format_attribute_value(
                        "123"
                    ),
                    "g.co/agent": self.agent_code,
                    "attr_key": _format_attribute_value("attr_value"),
                }
            ),
            "links": None,
            "status": None,
            "time_events": None,
            "start_time": None,
            "end_time": None,
            # pylint: disable=no-member
            "span_kind": ProtoSpan.SpanKind.INTERNAL,
        }

        client = mock.Mock()

        exporter = CloudTraceSpanExporter(self.project_id, client=client)

        exporter.export(span_datas)

        self.assertTrue(client.batch_write_spans.called)
        client.batch_write_spans.assert_called_with(
            "projects/{}".format(self.project_id), [cloud_trace_spans]
        )

    def test_extract_status_code_unset(self):
        self.assertIsNone(
            _extract_status(SpanStatus(status_code=StatusCode.UNSET))
        )

    def test_extract_status_code_ok(self):
        self.assertEqual(
            _extract_status(SpanStatus(status_code=StatusCode.OK)),
            Status(code=code_pb2.OK),
        )

    def test_extract_status_code_error(self):
        self.assertEqual(
            _extract_status(
                SpanStatus(
                    status_code=StatusCode.ERROR, description="error_desc",
                )
            ),
            Status(code=code_pb2.UNKNOWN, message="error_desc"),
        )

    def test_extract_status_code_future_added(self):
        self.assertEqual(
            _extract_status(SpanStatus(status_code=mock.Mock(),)),
            Status(code=code_pb2.UNKNOWN),
        )

    def test_extract_empty_attributes(self):
        self.assertEqual(
            _extract_attributes({}, num_attrs_limit=4),
            ProtoSpan.Attributes(attribute_map={}),
        )

    def test_extract_variety_of_attributes(self):
        self.assertEqual(
            _extract_attributes(
                self.attributes_variety_pack, num_attrs_limit=4
            ),
            self.extracted_attributes_variety_pack,
        )

    def test_extract_label_mapping_attributes(self):
        attributes_labels_mapping = {
            "http.scheme": "http",
            "http.host": "172.19.0.4:8000",
            "http.method": "POST",
            "http.request_content_length": 321,
            "http.response_content_length": 123,
            "http.route": "/fuzzy/search",
            "http.status_code": 200,
            "http.url": "http://172.19.0.4:8000/fuzzy/search",
            "http.user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36",
        }
        extracted_attributes_labels_mapping = ProtoSpan.Attributes(
            attribute_map={
                "/http/client_protocol": AttributeValue(
                    string_value=TruncatableString(
                        value="http", truncated_byte_count=0
                    )
                ),
                "/http/host": AttributeValue(
                    string_value=TruncatableString(
                        value="172.19.0.4:8000", truncated_byte_count=0
                    )
                ),
                "/http/method": AttributeValue(
                    string_value=TruncatableString(
                        value="POST", truncated_byte_count=0
                    )
                ),
                "/http/request/size": AttributeValue(int_value=321),
                "/http/response/size": AttributeValue(int_value=123),
                "/http/route": AttributeValue(
                    string_value=TruncatableString(
                        value="/fuzzy/search", truncated_byte_count=0
                    )
                ),
                "/http/status_code": AttributeValue(int_value=200),
                "/http/url": AttributeValue(
                    string_value=TruncatableString(
                        value="http://172.19.0.4:8000/fuzzy/search",
                        truncated_byte_count=0,
                    )
                ),
                "/http/user_agent": AttributeValue(
                    string_value=TruncatableString(
                        value="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36",
                        truncated_byte_count=0,
                    )
                ),
            }
        )
        self.assertEqual(
            _extract_attributes(attributes_labels_mapping, num_attrs_limit=9),
            extracted_attributes_labels_mapping,
        )

    def test_ignore_invalid_attributes(self):
        self.assertEqual(
            _extract_attributes(
                {"illegal_attribute_value": {}, "legal_attribute": 3},
                num_attrs_limit=4,
            ),
            ProtoSpan.Attributes(
                attribute_map={"legal_attribute": AttributeValue(int_value=3)},
                dropped_attributes_count=1,
            ),
        )

    def test_too_many_attributes(self):
        too_many_attrs = {}
        for attr_key in range(5):
            too_many_attrs[str(attr_key)] = 0
        proto_attrs = _extract_attributes(too_many_attrs, num_attrs_limit=4)
        self.assertEqual(proto_attrs.dropped_attributes_count, 1)

    def test_add_agent_attribute(self):
        self.assertEqual(
            _extract_attributes({}, num_attrs_limit=4, add_agent_attr=True),
            ProtoSpan.Attributes(
                attribute_map={"g.co/agent": self.agent_code},
                dropped_attributes_count=0,
            ),
        )

    def test_agent_attribute_priority(self):
        # Drop existing attributes in favor of the agent attribute
        self.assertEqual(
            _extract_attributes(
                {"attribute_key": "attr_value"},
                num_attrs_limit=1,
                add_agent_attr=True,
            ),
            ProtoSpan.Attributes(
                attribute_map={"g.co/agent": self.agent_code},
                dropped_attributes_count=1,
            ),
        )

    def test_attribute_value_truncation(self):
        self.assertEqual(
            _format_attribute_value(self.str_300),
            AttributeValue(
                string_value=TruncatableString(
                    value=self.str_256, truncated_byte_count=300 - 256
                )
            ),
        )

    def test_list_attribute_value(self):
        self.assertEqual(
            _format_attribute_value(("one", "two")),
            AttributeValue(
                string_value=TruncatableString(
                    value="one,two", truncated_byte_count=0
                )
            ),
        )
        self.assertEqual(
            _format_attribute_value([True]),
            AttributeValue(
                string_value=TruncatableString(
                    value="True", truncated_byte_count=0
                )
            ),
        )
        self.assertEqual(
            _format_attribute_value((2, 5)),
            AttributeValue(
                string_value=TruncatableString(
                    value="2,5", truncated_byte_count=0
                )
            ),
        )
        self.assertEqual(
            _format_attribute_value([2.0, 0.5, 4.55]),
            AttributeValue(
                string_value=TruncatableString(
                    value="2.0,0.5,4.55", truncated_byte_count=0
                )
            ),
        )

    def test_attribute_key_truncation(self):
        self.assertEqual(
            _extract_attributes(
                {self.str_300: "attr_value"}, num_attrs_limit=4
            ),
            ProtoSpan.Attributes(
                attribute_map={
                    self.str_128: AttributeValue(
                        string_value=TruncatableString(
                            value="attr_value", truncated_byte_count=0
                        )
                    )
                }
            ),
        )

    def test_extract_empty_events(self):
        self.assertIsNone(_extract_events([]))

    def test_too_many_events(self):
        event = Event(
            name="event", timestamp=self.example_time_in_ns, attributes={}
        )
        too_many_events = [event] * (MAX_NUM_EVENTS + 5)
        self.assertEqual(
            _extract_events(too_many_events),
            ProtoSpan.TimeEvents(
                time_event=[
                    {
                        "time": self.example_time_stamp,
                        "annotation": {
                            "description": TruncatableString(value="event",),
                            "attributes": {},
                        },
                    },
                ]
                * MAX_NUM_EVENTS,
                dropped_annotations_count=len(too_many_events)
                - MAX_NUM_EVENTS,
            ),
        )

    def test_too_many_event_attributes(self):
        event_attrs = {}
        for attr_key in range(MAX_EVENT_ATTRS + 5):
            event_attrs[str(attr_key)] = 0
        proto_events = _extract_events(
            [
                Event(
                    name="a",
                    attributes=event_attrs,
                    timestamp=self.example_time_in_ns,
                )
            ]
        )
        self.assertEqual(
            len(
                proto_events.time_event[0].annotation.attributes.attribute_map
            ),
            MAX_EVENT_ATTRS,
        )
        self.assertEqual(
            proto_events.time_event[
                0
            ].annotation.attributes.dropped_attributes_count,
            len(event_attrs) - MAX_EVENT_ATTRS,
        )

    def test_extract_multiple_events(self):
        event1 = Event(
            name="event1",
            attributes=self.attributes_variety_pack,
            timestamp=self.example_time_in_ns,
        )
        event2_nanos = 1589919438550020326
        event2 = Event(
            name="event2",
            attributes={"illegal_attr_value": dict()},
            timestamp=event2_nanos,
        )
        self.assertEqual(
            _extract_events([event1, event2]),
            ProtoSpan.TimeEvents(
                time_event=[
                    {
                        "time": self.example_time_stamp,
                        "annotation": {
                            "description": TruncatableString(
                                value="event1", truncated_byte_count=0
                            ),
                            "attributes": self.extracted_attributes_variety_pack,
                        },
                    },
                    {
                        "time": _get_time_from_ns(event2_nanos),
                        "annotation": {
                            "description": TruncatableString(
                                value="event2", truncated_byte_count=0
                            ),
                            "attributes": ProtoSpan.Attributes(
                                attribute_map={}, dropped_attributes_count=1
                            ),
                        },
                    },
                ]
            ),
        )

    def test_event_name_truncation(self):
        event1 = Event(
            name=self.str_300, attributes={}, timestamp=self.example_time_in_ns
        )
        self.assertEqual(
            _extract_events([event1]),
            ProtoSpan.TimeEvents(
                time_event=[
                    {
                        "time": self.example_time_stamp,
                        "annotation": {
                            "description": TruncatableString(
                                value=self.str_256,
                                truncated_byte_count=300 - 256,
                            ),
                            "attributes": {},
                        },
                    },
                ]
            ),
        )

    def test_extract_empty_links(self):
        self.assertIsNone(_extract_links([]))

    def test_extract_multiple_links(self):
        span_id1 = "95bb5edabd45950f"
        span_id2 = "b6b86ad2915c9ddc"
        link1 = Link(
            context=SpanContext(
                trace_id=int(self.example_trace_id, 16),
                span_id=int(span_id1, 16),
                is_remote=False,
            ),
            attributes={},
        )
        link2 = Link(
            context=SpanContext(
                trace_id=int(self.example_trace_id, 16),
                span_id=int(span_id1, 16),
                is_remote=False,
            ),
            attributes=self.attributes_variety_pack,
        )
        link3 = Link(
            context=SpanContext(
                trace_id=int(self.example_trace_id, 16),
                span_id=int(span_id2, 16),
                is_remote=False,
            ),
            attributes={"illegal_attr_value": dict(), "int_attr_value": 123},
        )
        self.assertEqual(
            _extract_links([link1, link2, link3]),
            ProtoSpan.Links(
                link=[
                    {
                        "trace_id": self.example_trace_id,
                        "span_id": span_id1,
                        "type": "TYPE_UNSPECIFIED",
                        "attributes": ProtoSpan.Attributes(attribute_map={}),
                    },
                    {
                        "trace_id": self.example_trace_id,
                        "span_id": span_id1,
                        "type": "TYPE_UNSPECIFIED",
                        "attributes": self.extracted_attributes_variety_pack,
                    },
                    {
                        "trace_id": self.example_trace_id,
                        "span_id": span_id2,
                        "type": "TYPE_UNSPECIFIED",
                        "attributes": {
                            "attribute_map": {
                                "int_attr_value": AttributeValue(int_value=123)
                            },
                            "dropped_attributes_count": 1,
                        },
                    },
                ]
            ),
        )

    def test_extract_link_with_none_attribute(self):
        link = Link(
            context=SpanContext(
                trace_id=int(self.example_trace_id, 16),
                span_id=int(self.example_span_id, 16),
                is_remote=False,
            ),
            attributes=None,
        )
        self.assertEqual(
            _extract_links([link]),
            ProtoSpan.Links(
                link=[
                    {
                        "trace_id": self.example_trace_id,
                        "span_id": self.example_span_id,
                        "type": "TYPE_UNSPECIFIED",
                        "attributes": ProtoSpan.Attributes(attribute_map={}),
                    },
                ]
            ),
        )

    def test_too_many_links(self):
        link = Link(
            context=SpanContext(
                trace_id=int(self.example_trace_id, 16),
                span_id=int(self.example_span_id, 16),
                is_remote=False,
            ),
            attributes={},
        )
        too_many_links = [link] * (MAX_NUM_LINKS + 5)
        self.assertEqual(
            _extract_links(too_many_links),
            ProtoSpan.Links(
                link=[
                    {
                        "trace_id": self.example_trace_id,
                        "span_id": self.example_span_id,
                        "type": "TYPE_UNSPECIFIED",
                        "attributes": {},
                    }
                ]
                * MAX_NUM_LINKS,
                dropped_links_count=len(too_many_links) - MAX_NUM_LINKS,
            ),
        )

    def test_too_many_link_attributes(self):
        link_attrs = {}
        for attr_key in range(MAX_LINK_ATTRS + 1):
            link_attrs[str(attr_key)] = 0
        attr_link = Link(
            context=SpanContext(
                trace_id=int(self.example_trace_id, 16),
                span_id=int(self.example_span_id, 16),
                is_remote=False,
            ),
            attributes=link_attrs,
        )

        proto_link = _extract_links([attr_link])
        self.assertEqual(
            len(proto_link.link[0].attributes.attribute_map), MAX_LINK_ATTRS
        )

    def test_extract_empty_resources(self):
        self.assertEqual(_extract_resources(Resource.get_empty()), {})

    def test_extract_well_formed_resources(self):
        resource = Resource(
            attributes={
                "cloud.account.id": 123,
                "host.id": "host",
                "cloud.zone": "US",
                "cloud.provider": "gcp",
                "extra_info": "extra",
                "gcp.resource_type": "gce_instance",
                "not_gcp_resource": "value",
            }
        )
        expected_extract = {
            "g.co/r/gce_instance/project_id": "123",
            "g.co/r/gce_instance/instance_id": "host",
            "g.co/r/gce_instance/zone": "US",
        }
        self.assertEqual(_extract_resources(resource), expected_extract)

    def test_extract_malformed_resources(self):
        # This resource doesn't have all the fields required for a gce_instance
        # Specifically its missing "host.id", "cloud.zone", "cloud.account.id"
        resource = Resource(
            attributes={
                "gcp.resource_type": "gce_instance",
                "cloud.provider": "gcp",
            }
        )
        # Should throw when passed a malformed GCP resource dict
        self.assertRaises(KeyError, _extract_resources, resource)

    def test_extract_unsupported_gcp_resources(self):
        # Unsupported gcp resources will be ignored
        resource = Resource(
            attributes={
                "cloud.account.id": "123",
                "host.id": "host",
                "extra_info": "extra",
                "not_gcp_resource": "value",
                "gcp.resource_type": "unsupported_gcp_resource",
                "cloud.provider": "gcp",
            }
        )
        self.assertEqual(_extract_resources(resource), {})

    def test_extract_unsupported_provider_resources(self):
        # Resources with currently unsupported providers will be ignored
        resource = Resource(
            attributes={
                "cloud.account.id": "123",
                "host.id": "host",
                "extra_info": "extra",
                "not_gcp_resource": "value",
                "cloud.provider": "aws",
            }
        )
        self.assertEqual(_extract_resources(resource), {})

    def test_truncate_string(self):
        """Cloud Trace API imposes limits on the length of many things,
        e.g. strings, number of events, number of attributes. We truncate
        these things before sending it to the API as an optimization.
        """
        self.assertEqual(_truncate_str("aaaa", limit=1), ("a", 3))
        self.assertEqual(_truncate_str("aaaa", limit=5), ("aaaa", 0))
        self.assertEqual(_truncate_str("aaaa", limit=4), ("aaaa", 0))
        self.assertEqual(_truncate_str("中文翻译", limit=4), ("中", 9))

    def test_strip_characters(self):
        self.assertEqual("0.10.0", _strip_characters("0.10.0b"))
        self.assertEqual("1.20.5", _strip_characters("1.20.5"))
        self.assertEqual("3.1.0", _strip_characters("3.1.0beta"))
        self.assertEqual("4.2.0", _strip_characters("4b.2rc.0a"))
        self.assertEqual("6.20.15", _strip_characters("b6.20.15"))

    # pylint: disable=no-member
    def test_extract_span_kind(self):
        self.assertEqual(
            _extract_span_kind(SpanKind.INTERNAL), ProtoSpan.SpanKind.INTERNAL
        )
        self.assertEqual(
            _extract_span_kind(SpanKind.CLIENT), ProtoSpan.SpanKind.CLIENT
        )
        self.assertEqual(
            _extract_span_kind(SpanKind.SERVER), ProtoSpan.SpanKind.SERVER
        )
        self.assertEqual(
            _extract_span_kind(SpanKind.CONSUMER), ProtoSpan.SpanKind.CONSUMER
        )
        self.assertEqual(
            _extract_span_kind(SpanKind.PRODUCER), ProtoSpan.SpanKind.PRODUCER
        )
        self.assertEqual(
            _extract_span_kind(-1), ProtoSpan.SpanKind.SPAN_KIND_UNSPECIFIED
        )
