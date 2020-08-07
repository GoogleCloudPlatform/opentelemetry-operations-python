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
    NANOS_PER_SECOND,
    WRITE_INTERVAL,
    CloudMonitoringMetricsExporter,
)
from opentelemetry.sdk import metrics
from opentelemetry.sdk.metrics.export import MetricRecord, MetricsExportResult
from opentelemetry.sdk.metrics.export.aggregate import SumAggregator


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
        args = ["mock_server", "-address", self.address]
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
        exporter = CloudMonitoringMetricsExporter(
            self.project_id, client=MetricServiceClient(transport=transport)
        )

        meter = metrics.MeterProvider().get_meter(__name__)
        counter = meter.create_metric(
            name="name",
            description="desc",
            unit="1",
            value_type=int,
            metric_type=metrics.Counter,
        )

        sum_agg = SumAggregator()
        sum_agg.checkpoint = 1
        sum_agg.last_update_timestamp = (WRITE_INTERVAL + 2) * NANOS_PER_SECOND

        result = exporter.export(
            [MetricRecord(counter, labels=(), aggregator=sum_agg,)]
        )

        self.assertEqual(result, MetricsExportResult.SUCCESS)
