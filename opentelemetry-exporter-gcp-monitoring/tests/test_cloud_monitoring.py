# pylint: disable=too-many-statements
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

"""
Some tests in this file use [syrupy](https://github.com/tophat/syrupy) for snapshot testing aka
golden testing. The GCM API calls are captured with a gRPC fake and compared to the existing
snapshot file in the __snapshots__ directory.

If an expected behavior change is made to the exporter causing these tests to fail, regenerate
the snapshots by running tox to pass the --snapshot-update flag to pytest:

```sh
tox -e py310-ci-test-cloudmonitoring -- --snapshot-update
```

Be sure to review the changes.
"""

from typing import Iterable

import pytest
from fixtures.gcmfake import GcmFake
from google.auth.credentials import AnonymousCredentials
from google.cloud.monitoring_v3 import MetricServiceClient
from opentelemetry.exporter.cloud_monitoring import (
    CloudMonitoringMetricsExporter,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.util.types import Attributes

PROJECT_ID = "fakeproject"
LABELS: Attributes = {
    "string": "string",
    "int": 123,
    "float": 123.4,
}


@pytest.fixture(name="meter_provider")
def fixture_meter_provider(gcmfake: GcmFake) -> Iterable[MeterProvider]:
    mp = MeterProvider(
        metric_readers=[
            PeriodicExportingMetricReader(
                CloudMonitoringMetricsExporter(
                    project_id=PROJECT_ID, client=gcmfake.client
                )
            )
        ],
        shutdown_on_exit=False,
    )
    yield mp
    mp.shutdown()


def test_create_monitoring_exporter() -> None:
    client = MetricServiceClient(credentials=AnonymousCredentials())
    CloudMonitoringMetricsExporter(project_id=PROJECT_ID, client=client)


def test_counter(
    meter_provider: MeterProvider,
    gcmfake: GcmFake,
    snapshot_gcmcalls,
) -> None:
    counter = meter_provider.get_meter(__name__).create_counter(
        "mycounter", description="foo", unit="{myunit}"
    )
    counter.add(123, LABELS)
    meter_provider.force_flush()
    assert gcmfake.get_calls() == snapshot_gcmcalls
