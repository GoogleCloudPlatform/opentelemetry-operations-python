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

import grpc
from google.cloud.trace_v2 import TraceServiceClient
from google.cloud.trace_v2.gapic.transports import trace_service_grpc_transport
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import _Span as Span
from opentelemetry.sdk.trace.export import SpanExportResult
from opentelemetry.trace import SpanContext, SpanKind

from test_common import BaseExporterIntegrationTest, time_ns


class TestCloudTraceSpanExporter(BaseExporterIntegrationTest):
    def test_export(self):
        trace_id = "6e0c63257de34c92bf9efcd03927272e"
        span_id = "95bb5edabd45950f"

        # Create span and associated data.
        resource_info = Resource(
            {
                "cloud.account.id": 123,
                "host.id": "host",
                "cloud.zone": "US",
                "cloud.provider": "gcp",
                "gcp.resource_type": "gce_instance",
            }
        )
        span = Span(
            name="span_name",
            context=SpanContext(
                trace_id=int(trace_id, 16),
                span_id=int(span_id, 16),
                is_remote=False,
            ),
            parent=None,
            kind=SpanKind.INTERNAL,
            resource=resource_info,
            attributes={"attr_key": "attr_value"},
        )

        # pylint: disable=protected-access
        span._start_time = int(time_ns() - (60 * 1e9))
        span._end_time = time_ns()
        span_data = [span]

        # Setup the trace exporter.
        channel = grpc.insecure_channel(self.address)
        transport = trace_service_grpc_transport.TraceServiceGrpcTransport(
            channel=channel
        )
        client = TraceServiceClient(transport=transport)
        trace_exporter = CloudTraceSpanExporter(self.project_id, client=client)

        # Export the spans and verify the results.
        result = trace_exporter.export(span_data)
        self.assertEqual(result, SpanExportResult.SUCCESS)
