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

import socket
import subprocess
import unittest

import grpc
from google.cloud.trace_v2 import TraceServiceClient
from google.cloud.trace_v2.gapic.transports import trace_service_grpc_transport
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import Span, SpanExportResult
from opentelemetry.trace import SpanContext, SpanKind


class TestCloudTraceSpanExporter(unittest.TestCase):
    @staticmethod
    def get_free_port():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("localhost", 0))
        port = sock.getsockname()[1]
        sock.close()
        return port

    def start_server(self):
        port = self.get_free_port()

        args = "./mock_server-x64-linux -address=localhost:" + str(port)
        subprocess.Popen(args, shell=True)

        return port

    @staticmethod
    def stop_server(port):
        args = "fuser -k " + str(port) + "/tcp"
        subprocess.Popen(args, shell=True)

    def test_export(self):
        port = self.start_server()

        project_id = "TEST-PROJECT"
        trace_id = "6e0c63257de34c92bf9efcd03927272e"
        span_id = "95bb5edabd45950f"
        resource_info = Resource(
            {
                "cloud.account.id": 123,
                "host.id": "host",
                "cloud.zone": "US",
                "cloud.provider": "gcp",
                "gcp.resource_type": "gce_instance",
            }
        )
        span_data = [
            Span(
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
        ]

        mock_server_address = "localhost:" + str(port)
        channel = grpc.insecure_channel(mock_server_address)
        transport = trace_service_grpc_transport.TraceServiceGrpcTransport(
            channel=channel
        )
        client = TraceServiceClient(transport=transport)

        exporter = CloudTraceSpanExporter(project_id, client=client)
        result = exporter.export(span_data)

        self.assertEqual(result, SpanExportResult.SUCCESS)

        self.stop_server(port)
