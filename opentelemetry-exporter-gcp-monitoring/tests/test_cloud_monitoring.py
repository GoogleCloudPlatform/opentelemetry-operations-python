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

from typing import List, Union

import pytest
from fixtures.gcmfake import GcmFake, GcmFakeMeterProvider
from google.auth.credentials import AnonymousCredentials
from google.cloud.monitoring_v3 import MetricServiceClient
from opentelemetry.exporter.cloud_monitoring import (
    CloudMonitoringMetricsExporter,
)
from opentelemetry.metrics import CallbackOptions, Observation
from opentelemetry.sdk.metrics.view import (
    ExplicitBucketHistogramAggregation,
    ExponentialBucketHistogramAggregation,
    View,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.util.types import Attributes

PROJECT_ID = "fakeproject"
LABELS: Attributes = {
    "string": "string",
    "int": 123,
    "float": 123.4,
}


def test_create_monitoring_exporter() -> None:
    client = MetricServiceClient(credentials=AnonymousCredentials())
    CloudMonitoringMetricsExporter(project_id=PROJECT_ID, client=client)
    CloudMonitoringMetricsExporter(
        project_id=PROJECT_ID,
        client=client,
        prefix="custom.googleapis.com",
    )


@pytest.mark.parametrize(
    "value", [pytest.param(123, id="int"), pytest.param(45.6, id="float")]
)
def test_counter(
    value: Union[float, int],
    gcmfake_meter_provider: GcmFakeMeterProvider,
    gcmfake: GcmFake,
    snapshot_gcmcalls,
) -> None:
    meter_provider = gcmfake_meter_provider()
    counter = meter_provider.get_meter(__name__).create_counter(
        "mycounter", description="foo", unit="{myunit}"
    )
    counter.add(value, LABELS)
    meter_provider.force_flush()
    assert gcmfake.get_calls() == snapshot_gcmcalls


@pytest.mark.parametrize(
    "value", [pytest.param(123, id="int"), pytest.param(45.6, id="float")]
)
def test_up_down_counter(
    value: Union[float, int],
    gcmfake_meter_provider: GcmFakeMeterProvider,
    gcmfake: GcmFake,
    snapshot_gcmcalls,
) -> None:
    meter_provider = gcmfake_meter_provider()
    updowncounter = meter_provider.get_meter(__name__).create_up_down_counter(
        "myupdowncounter", description="foo", unit="{myunit}"
    )
    updowncounter.add(value, LABELS)
    meter_provider.force_flush()
    assert gcmfake.get_calls() == snapshot_gcmcalls


def test_histogram_default_buckets(
    gcmfake_meter_provider: GcmFakeMeterProvider,
    gcmfake: GcmFake,
    snapshot_gcmcalls,
) -> None:
    meter_provider = gcmfake_meter_provider()
    histogram = meter_provider.get_meter(__name__).create_histogram(
        "myhistogram", description="foo", unit="{myunit}"
    )
    for value in range(10_000):
        histogram.record(value, LABELS)

    meter_provider.force_flush()
    assert gcmfake.get_calls() == snapshot_gcmcalls


def test_histogram_single_bucket(
    gcmfake_meter_provider: GcmFakeMeterProvider,
    gcmfake: GcmFake,
    snapshot_gcmcalls,
) -> None:
    meter_provider = gcmfake_meter_provider(
        views=[
            View(
                instrument_name="myhistogram",
                aggregation=ExplicitBucketHistogramAggregation(
                    boundaries=[5.5]
                ),
            )
        ]
    )
    histogram = meter_provider.get_meter(__name__).create_histogram(
        "myhistogram", description="foo", unit="{myunit}"
    )
    for value in range(10_000):
        histogram.record(value, LABELS)

    meter_provider.force_flush()
    assert gcmfake.get_calls() == snapshot_gcmcalls


def test_exponential_histogram(
    gcmfake_meter_provider: GcmFakeMeterProvider,
    gcmfake: GcmFake,
    snapshot_gcmcalls,
) -> None:
    meter_provider = gcmfake_meter_provider(
        views=[
            View(
                instrument_name="myexponentialhistogram",
                aggregation=ExponentialBucketHistogramAggregation(
                    max_size=160, max_scale=20
                ),
            )
        ]
    )
    histogram = meter_provider.get_meter(__name__).create_histogram(
        "myexponentialhistogram", description="foo", unit="{myunit}"
    )

    for value in [100, 50, 200, 25, 300, 75, 150]:
        histogram.record(value, LABELS)

    meter_provider.force_flush()
    assert gcmfake.get_calls() == snapshot_gcmcalls


@pytest.mark.parametrize(
    "value", [pytest.param(123, id="int"), pytest.param(45.6, id="float")]
)
def test_observable_counter(
    value: Union[float, int],
    gcmfake_meter_provider: GcmFakeMeterProvider,
    gcmfake: GcmFake,
    snapshot_gcmcalls,
) -> None:
    def callback(_: CallbackOptions) -> List[Observation]:
        return [Observation(value, LABELS)]

    meter_provider = gcmfake_meter_provider()
    meter_provider.get_meter(__name__).create_observable_counter(
        "myobservablecounter",
        callbacks=[callback],
        description="foo",
        unit="{myunit}",
    )
    meter_provider.force_flush()
    assert gcmfake.get_calls() == snapshot_gcmcalls


@pytest.mark.parametrize(
    "value", [pytest.param(123, id="int"), pytest.param(45.6, id="float")]
)
def test_observable_updowncounter(
    value: Union[float, int],
    gcmfake_meter_provider: GcmFakeMeterProvider,
    gcmfake: GcmFake,
    snapshot_gcmcalls,
) -> None:
    def callback(_: CallbackOptions) -> List[Observation]:
        return [Observation(value, LABELS)]

    meter_provider = gcmfake_meter_provider()
    meter_provider.get_meter(__name__).create_observable_up_down_counter(
        "myobservableupdowncounter",
        callbacks=[callback],
        description="foo",
        unit="{myunit}",
    )
    meter_provider.force_flush()
    assert gcmfake.get_calls() == snapshot_gcmcalls


@pytest.mark.parametrize(
    "value", [pytest.param(123, id="int"), pytest.param(45.6, id="float")]
)
def test_observable_gauge(
    value: Union[float, int],
    gcmfake_meter_provider: GcmFakeMeterProvider,
    gcmfake: GcmFake,
    snapshot_gcmcalls,
) -> None:
    def callback(_: CallbackOptions) -> List[Observation]:
        return [Observation(value, LABELS)]

    meter_provider = gcmfake_meter_provider()
    meter_provider.get_meter(__name__).create_observable_gauge(
        "myobservablegauge",
        callbacks=[callback],
        description="foo",
        unit="{myunit}",
    )
    meter_provider.force_flush()
    assert gcmfake.get_calls() == snapshot_gcmcalls


def test_invalid_label_keys(
    gcmfake_meter_provider: GcmFakeMeterProvider,
    gcmfake: GcmFake,
    snapshot_gcmcalls,
) -> None:
    meter_provider = gcmfake_meter_provider()
    counter = meter_provider.get_meter(__name__).create_counter(
        "mycounter", description="foo", unit="{myunit}"
    )
    counter.add(12, {"1some.invalid$\\key": "value"})
    meter_provider.force_flush()
    assert gcmfake.get_calls() == snapshot_gcmcalls


# See additional tests in test_resource.py
def test_with_resource(
    gcmfake_meter_provider: GcmFakeMeterProvider,
    gcmfake: GcmFake,
    snapshot_gcmcalls,
) -> None:
    meter_provider = gcmfake_meter_provider(
        resource=Resource.create(
            {
                "cloud.platform": "gcp_kubernetes_engine",
                "cloud.availability_zone": "myavailzone",
                "k8s.cluster.name": "mycluster",
                "k8s.namespace.name": "myns",
                "k8s.pod.name": "mypod",
                "k8s.container.name": "mycontainer",
            },
        )
    )
    counter = meter_provider.get_meter(__name__).create_counter(
        "mycounter", description="foo", unit="{myunit}"
    )
    counter.add(12, LABELS)
    meter_provider.force_flush()
    assert gcmfake.get_calls() == snapshot_gcmcalls
