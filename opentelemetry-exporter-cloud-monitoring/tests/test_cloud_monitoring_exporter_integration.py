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
from google.cloud.monitoring_v3 import MetricServiceClient
from google.cloud.monitoring_v3.gapic.transports import (
    metric_service_grpc_transport,
)
from opentelemetry.exporter.cloud_monitoring import (
    CloudMonitoringMetricsExporter,
)
from opentelemetry.sdk.metrics.export import MetricRecord, MetricsExportResult
from tests.test_cloud_monitoring import MockMetric, UnsupportedAggregator


# TODO: #46
# Refactor duplicated code found in test_integration_cloud_trace_exporter.py
class BaseExporterIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.project_id = "TEST-PROJECT"

        # Find a free port to spin up our server at.
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("localhost", 0))
        self.address = "localhost:" + str(sock.getsockname()[1])
        sock.close()

        # Start the mock server.
        args = ["mock_server-x64-linux-v0-alpha", "-address", self.address]
        self.mock_server_process = subprocess.Popen(
            args, stderr=subprocess.PIPE
        )
        # Block until the mock server starts (it will output the address after starting).
        self.mock_server_process.stderr.readline()

    def tearDown(self):
        self.mock_server_process.kill()


class TestCloudMonitoringSpanExporter(BaseExporterIntegrationTest):
    def test_export(self):
        channel = grpc.insecure_channel(self.address)
        transport = metric_service_grpc_transport.MetricServiceGrpcTransport(
            channel=channel
        )
        client = MetricServiceClient(transport=transport)

        exporter = CloudMonitoringMetricsExporter(
            self.project_id, client=client
        )
        result = exporter.export(
            [
                MetricRecord(
                    MockMetric(),
                    (("label1", "value1"),),
                    UnsupportedAggregator(),
                )
            ]
        )

        self.assertEqual(result, MetricsExportResult.SUCCESS)
