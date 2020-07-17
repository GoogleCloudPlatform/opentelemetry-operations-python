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
from opentelemetry.sdk.resources import Resource


class UnsupportedAggregator:
    pass


class MockMeter:
    def __init__(self, resource=Resource.create_empty()):
        self.resource = resource


class MockMetric:
    def __init__(
        self,
        name="name",
        description="description",
        value_type=int,
        meter=None,
    ):
        self.name = name
        self.description = description
        self.value_type = value_type
        self.meter = meter or MockMeter()


class TestCloudMonitoringSpanExporter(unittest.TestCase):
    def test_export(self):
        project_id = "TEST-PROJECT"
        mock_server_address = "localhost:8080"
        channel = grpc.insecure_channel(mock_server_address)
        transport = metric_service_grpc_transport.MetricServiceGrpcTransport(
            channel=channel
        )
        client = MetricServiceClient(transport=transport)

        exporter = CloudMonitoringMetricsExporter(project_id, client=client)
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
