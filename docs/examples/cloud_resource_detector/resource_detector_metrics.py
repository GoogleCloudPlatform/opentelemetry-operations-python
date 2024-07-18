#!/usr/bin/env python3
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

import time

from opentelemetry import metrics
from opentelemetry.exporter.cloud_monitoring import (
    CloudMonitoringMetricsExporter,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import get_aggregated_resources
from opentelemetry.resourcedetector.gcp_resource_detector import (
    GoogleCloudResourceDetector,
)

resource = get_aggregated_resources(
    [GoogleCloudResourceDetector(raise_on_error=True)]
)

meter_provider = MeterProvider(
    resource=resource,
    metric_readers=[
        PeriodicExportingMetricReader(
            CloudMonitoringMetricsExporter(), export_interval_millis=5000
        )
    ],
)
metrics.set_meter_provider(meter_provider)
meter = metrics.get_meter(__name__)

requests_counter = meter.create_counter(
    name="request_counter_with_resource",
    description="number of requests",
    unit="1",
)

staging_labels = {"environment": "staging"}

for i in range(20):
    requests_counter.add(25, staging_labels)
    time.sleep(10)
