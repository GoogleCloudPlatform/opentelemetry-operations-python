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


import logging
from unittest.mock import MagicMock, patch

import grpc
from google.cloud.monitoring_v3 import MetricServiceClient
from google.cloud.monitoring_v3.gapic.transports import (
    metric_service_grpc_transport,
)
from opentelemetry.exporter.cloud_monitoring import (
    CloudMonitoringMetricsExporter,
)
from opentelemetry.sdk import metrics
from opentelemetry.sdk.metrics.export.controller import PushController
from opentelemetry.sdk.resources import Resource

from test_common import BaseExporterIntegrationTest

logger = logging.getLogger(__name__)


class TestCloudMonitoringSpanExporter(BaseExporterIntegrationTest):
    def test_export(self):
        channel = grpc.insecure_channel(self.address)
        transport = metric_service_grpc_transport.MetricServiceGrpcTransport(
            channel=channel
        )
        client = MagicMock(wraps=MetricServiceClient(transport=transport))
        exporter = CloudMonitoringMetricsExporter(
            self.project_id, client=client
        )

        meter_provider = metrics.MeterProvider(
            resource=Resource.create(
                {
                    "cloud.account.id": "some_account_id",
                    "cloud.provider": "gcp",
                    "cloud.zone": "us-east1-b",
                    "host.id": 654321,
                    "gcp.resource_type": "gce_instance",
                }
            )
        )
        meter = meter_provider.get_meter(__name__)
        counter = meter.create_counter(
            # TODO: remove "opentelemetry/" prefix which is a hack
            # https://github.com/GoogleCloudPlatform/opentelemetry-operations-python/issues/84
            name="opentelemetry/name",
            description="desc",
            unit="1",
            value_type=int,
        )
        # interval doesn't matter, we don't start the thread and just run
        # tick() instead
        controller = PushController(meter, exporter, 10)

        counter.add(10, {"env": "test"})

        with patch(
            "opentelemetry.exporter.cloud_monitoring.logger"
        ) as mock_logger:
            controller.tick()

            # run tox tests with `-- -log-cli-level=0` to see mock calls made
            logger.debug(client.create_time_series.mock_calls)
            mock_logger.warning.assert_not_called()
            mock_logger.error.assert_not_called()
