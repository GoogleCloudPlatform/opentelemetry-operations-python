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

import unittest
from typing import Optional
from unittest import mock

from google.api.label_pb2 import LabelDescriptor
from google.api.metric_pb2 import MetricDescriptor
from google.api.monitored_resource_pb2 import MonitoredResource
from google.cloud.monitoring_v3.proto.metric_pb2 import TimeSeries
from opentelemetry.attributes import BoundedAttributes
from opentelemetry.exporter.cloud_monitoring import (
    MAX_BATCH_WRITE,
    NANOS_PER_SECOND,
    UNIQUE_IDENTIFIER_KEY,
    WRITE_INTERVAL,
    CloudMonitoringMetricsExporter,
)
from opentelemetry.sdk._metrics import MeterProvider
from opentelemetry.sdk._metrics.point import (
    AggregationTemporality,
    Sum,
)
from opentelemetry.sdk.resources import Resource

import metrictestutil


class UnsupportedAggregator:
    pass


class MockBatcher:
    def __init__(self, stateful):
        self.stateful = stateful


def mock_meter(stateful: Optional[bool] = None):
    # create an autospec of Meter from an instance in order to capture instance
    # variables (meter.processor)
    meter = MeterProvider().get_meter(__name__)
    meter_mock = mock.create_autospec(meter, spec_set=True)
    return meter_mock


class MockMetric:
    def __init__(
        self,
        name="name",
        description="description",
        meter=None,
    ):
        self.name = name
        self.description = description
        self.meter = meter or mock_meter()


# pylint: disable=protected-access
# pylint can't deal with ProtoBuf object members
# pylint: disable=no-member


class TestCloudMonitoringMetricsExporter(unittest.TestCase):
    def setUp(self):
        self.client_patcher = mock.patch(
            "opentelemetry.exporter.cloud_monitoring.MetricServiceClient"
        )
        self.client_patcher.start()

    def tearDown(self) -> None:
        self.client_patcher.stop()

    @classmethod
    def setUpClass(cls):
        cls.project_id = "PROJECT"
        cls.project_name = "PROJECT_NAME"

    def test_constructor_default(self):
        exporter = CloudMonitoringMetricsExporter(self.project_id)
        self.assertEqual(exporter.project_id, self.project_id)

    def test_constructor_explicit(self):
        client = mock.Mock()
        exporter = CloudMonitoringMetricsExporter(
            self.project_id, client=client
        )

        self.assertIs(exporter.client, client)
        self.assertEqual(exporter.project_id, self.project_id)

    def test_batch_write(self):
        client = mock.Mock()
        exporter = CloudMonitoringMetricsExporter(
            project_id=self.project_id, client=client
        )
        exporter.project_name = self.project_name
        exporter._batch_write(range(2 * MAX_BATCH_WRITE + 1))
        client.create_time_series.assert_has_calls(
            [
                mock.call(self.project_name, range(MAX_BATCH_WRITE)),
                mock.call(
                    self.project_name,
                    range(MAX_BATCH_WRITE, 2 * MAX_BATCH_WRITE),
                ),
                mock.call(
                    self.project_name,
                    range(2 * MAX_BATCH_WRITE, 2 * MAX_BATCH_WRITE + 1),
                ),
            ]
        )

        exporter._batch_write(range(MAX_BATCH_WRITE))
        client.create_time_series.assert_has_calls(
            [mock.call(self.project_name, range(MAX_BATCH_WRITE))]
        )

        exporter._batch_write(range(MAX_BATCH_WRITE - 1))
        client.create_time_series.assert_has_calls(
            [mock.call(self.project_name, range(MAX_BATCH_WRITE - 1))]
        )

    def test_get_metric_descriptor(self):
        client = mock.Mock()
        exporter = CloudMonitoringMetricsExporter(
            project_id=self.project_id, client=client
        )
        exporter.project_name = self.project_name

        self.assertIsNone(
            exporter._get_metric_descriptor(
                metrictestutil._generate_unsupported_metric("name")
            )
        )

        metric = metrictestutil._generate_sum(
            "name",
            0,
            attributes=BoundedAttributes(attributes={"label1": "value1"}),
            description="description",
        )
        metric_descriptor = exporter._get_metric_descriptor(metric)
        client.create_metric_descriptor.assert_called_with(
            self.project_name,
            MetricDescriptor(
                **{
                    "name": None,
                    "type": "custom.googleapis.com/OpenTelemetry/name",
                    "display_name": "name",
                    "description": "description",
                    "labels": [
                        LabelDescriptor(key="label1", value_type="STRING")
                    ],
                    "metric_kind": "CUMULATIVE",
                    "value_type": "INT64",
                }
            ),
        )

        # Getting a cached metric descriptor shouldn't use another call
        cached_metric_descriptor = exporter._get_metric_descriptor(metric)
        self.assertEqual(client.create_metric_descriptor.call_count, 1)
        self.assertEqual(metric_descriptor, cached_metric_descriptor)

        # Drop labels with values that aren't string, int or bool
        exporter._get_metric_descriptor(
            metrictestutil._generate_sum(
                "name2",
                0.0,
                attributes=BoundedAttributes(
                    attributes={
                        "label1": "value1",
                        "label2": dict(),
                        "label3": 0,
                        "label4": True,
                    }
                ),
                description="description",
            )
        )
        client.create_metric_descriptor.assert_called_with(
            self.project_name,
            MetricDescriptor(
                **{
                    "name": None,
                    "type": "custom.googleapis.com/OpenTelemetry/name2",
                    "display_name": "name2",
                    "description": "description",
                    "labels": [
                        LabelDescriptor(key="label1", value_type="STRING"),
                        LabelDescriptor(key="label3", value_type="INT64"),
                        LabelDescriptor(key="label4", value_type="BOOL"),
                    ],
                    "metric_kind": "CUMULATIVE",
                    "value_type": "DOUBLE",
                }
            ),
        )

    def test_get_value_observer_metric_descriptor(self):
        client = mock.Mock()
        exporter = CloudMonitoringMetricsExporter(
            project_id=self.project_id, client=client
        )
        exporter.project_name = self.project_name
        metric = metrictestutil._generate_gauge(
            "name",
            0,
            attributes=BoundedAttributes(attributes={}),
            description="description",
        )
        exporter._get_metric_descriptor(metric)
        client.create_metric_descriptor.assert_called_with(
            self.project_name,
            MetricDescriptor(
                **{
                    "name": None,
                    "type": "custom.googleapis.com/OpenTelemetry/name",
                    "display_name": "name",
                    "description": "description",
                    "labels": [],
                    "metric_kind": "GAUGE",
                    "value_type": "INT64",
                }
            ),
        )

    def test_export(self):
        client = mock.Mock()

        with mock.patch(
            "opentelemetry.exporter.cloud_monitoring.time_ns",
            lambda: NANOS_PER_SECOND,
        ):
            exporter = CloudMonitoringMetricsExporter(
                project_id=self.project_id, client=client
            )

        exporter.project_name = self.project_name

        client.create_metric_descriptor.return_value = MetricDescriptor(
            **{
                "name": None,
                "type": "custom.googleapis.com/OpenTelemetry/name",
                "display_name": "name",
                "description": "description",
                "labels": [
                    LabelDescriptor(key="label1", value_type="STRING"),
                    LabelDescriptor(key="label2", value_type="INT64"),
                ],
                "metric_kind": "CUMULATIVE",
                "value_type": "DOUBLE",
            }
        )

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

        exporter.export(
            [
                metrictestutil._generate_sum(
                    "name",
                    1,
                    attributes=BoundedAttributes(
                        attributes={"label1": "value1", "label2": 1}
                    ),
                    description="description",
                    resource=resource,
                ),
                metrictestutil._generate_sum(
                    "name",
                    1,
                    attributes=BoundedAttributes(
                        attributes={"label1": "value2", "label2": 2}
                    ),
                    description="description",
                    resource=resource
                )
            ]
        )
        expected_resource = MonitoredResource(
            type="gce_instance",
            labels={"project_id": "123", "instance_id": "host", "zone": "US"},
        )

        series1 = TimeSeries(resource=expected_resource)
        series1.metric_kind = MetricDescriptor.MetricKind.CUMULATIVE
        series1.metric.type = "custom.googleapis.com/OpenTelemetry/name"
        series1.metric.labels["label1"] = "value1"
        series1.metric.labels["label2"] = "1"
        point = series1.points.add()
        point.value.int64_value = 1
        point.interval.end_time.seconds = 1641946016
        point.interval.end_time.nanos = 139533244
        point.interval.start_time.seconds = 1641946015
        point.interval.start_time.nanos = 139533244

        series2 = TimeSeries(resource=expected_resource)
        series2.metric_kind = MetricDescriptor.MetricKind.CUMULATIVE
        series2.metric.type = "custom.googleapis.com/OpenTelemetry/name"
        series2.metric.labels["label1"] = "value2"
        series2.metric.labels["label2"] = "2"
        point = series2.points.add()
        point.value.int64_value = 1
        point.interval.end_time.seconds = 1641946016
        point.interval.end_time.nanos = 139533244
        point.interval.start_time.seconds = 1641946015
        point.interval.start_time.nanos = 139533244

        client.create_time_series.assert_has_calls(
            [mock.call(self.project_name, [series1, series2])]
        )

        # Attempting to export too soon after another export with the exact
        # same labels leads to it being dropped

        exporter.export(
            [
                metrictestutil._generate_sum(
                    "name",
                    1,
                    attributes=BoundedAttributes(
                        attributes={"label1": "value1", "label2": 1}
                    ),
                    description="description",
                ),
                metrictestutil._generate_sum(
                    "name",
                    1,
                    attributes=BoundedAttributes(
                        attributes={"label1": "value2", "label2": 2}
                    ),
                    description="description",
                )
            ]
        )
        self.assertEqual(client.create_time_series.call_count, 1)

        # But exporting with different labels is fine
        exporter.export(
            [
                metrictestutil._generate_sum(
                    "name",
                    2,
                    attributes=BoundedAttributes(
                        attributes={"label1": "changed_label", "label2": 2}
                    ),
                    description="description",
                )
            ]
        )
        series3 = TimeSeries()
        series3.metric_kind = MetricDescriptor.MetricKind.CUMULATIVE
        series3.metric.type = "custom.googleapis.com/OpenTelemetry/name"
        series3.metric.labels["label1"] = "changed_label"
        series3.metric.labels["label2"] = "2"
        point = series3.points.add()
        point.value.int64_value = 2
        point.interval.end_time.seconds = 1641946016
        point.interval.end_time.nanos = 139533244
        point.interval.start_time.seconds = 1641946015
        point.interval.start_time.nanos = 139533244

        client.create_time_series.assert_has_calls(
            [
                mock.call(self.project_name, [series1, series2]),
                mock.call(self.project_name, [series3]),
            ]
        )

    def test_export_value_observer(self):
        client = mock.Mock()

        with mock.patch(
            "opentelemetry.exporter.cloud_monitoring.time_ns",
            lambda: NANOS_PER_SECOND,
        ):
            exporter = CloudMonitoringMetricsExporter(
                project_id=self.project_id, client=client
            )

        exporter.project_name = self.project_name

        client.create_metric_descriptor.return_value = MetricDescriptor(
            **{
                "name": None,
                "type": "custom.googleapis.com/OpenTelemetry/name",
                "display_name": "name",
                "description": "description",
                "labels": [],
                "metric_kind": "GAUGE",
                "value_type": "INT64",
            }
        )

        exporter.export(
            [
                metrictestutil._generate_gauge(
                    "name",
                    5,
                    attributes=BoundedAttributes(attributes={}),
                    description="description",
                )
            ]
        )

        series = TimeSeries()
        series.metric_kind = MetricDescriptor.MetricKind.GAUGE
        series.metric.type = "custom.googleapis.com/OpenTelemetry/name"
        point = series.points.add()
        point.value.int64_value = 5
        point.interval.end_time.seconds = 1641946016
        point.interval.end_time.nanos = 139533244
        point.interval.start_time.seconds = 1641946016
        point.interval.start_time.nanos = 139533244
        client.create_time_series.assert_has_calls(
            [mock.call(self.project_name, [series])]
        )

    def test_export_histogram(self):
        client = mock.Mock()

        with mock.patch(
            "opentelemetry.exporter.cloud_monitoring.time_ns",
            lambda: NANOS_PER_SECOND,
        ):
            exporter = CloudMonitoringMetricsExporter(
                project_id=self.project_id, client=client
            )

        exporter.project_name = self.project_name

        client.create_metric_descriptor.return_value = MetricDescriptor(
            **{
                "name": None,
                "type": "custom.googleapis.com/OpenTelemetry/name",
                "display_name": "name",
                "description": "description",
                "labels": [],
                "metric_kind": "CUMULATIVE",
                "value_type": "DISTRIBUTION",
            }
        )

        exporter.export(
            [
                metrictestutil._generate_histogram(
                    "name",
                    [1, 2, 4, 3],
                    [0, 2, 4, 6],
                    0.5,
                    6.5,
                    10,
                    attributes=BoundedAttributes(attributes={}),
                    description="description",
                )
            ]
        )

        series = TimeSeries()
        series.metric_kind = MetricDescriptor.MetricKind.CUMULATIVE
        series.metric.type = "custom.googleapis.com/OpenTelemetry/name"
        point = {
            "interval": {
                "start_time": {"seconds": 1641946015, "nanos": 139533244},
                "end_time": {"seconds": 1641946016, "nanos": 139533244},
            },
            "value": {
                "distribution_value": {
                    "count": 10,
                    "bucket_options": {
                        "explicit_buckets": {"bounds": [0.0, 2.0, 4.0, 6.0]}
                    },
                    "bucket_counts": [1, 2, 4, 3],
                }
            },
        }
        series.points.add(**point)
        client.create_time_series.assert_has_calls(
            [mock.call(self.project_name, [series])]
        )

    def test_stateless_times(self):
        client = mock.Mock()
        with mock.patch(
            "opentelemetry.exporter.cloud_monitoring.time_ns",
            lambda: NANOS_PER_SECOND,
        ):
            exporter = CloudMonitoringMetricsExporter(
                project_id=self.project_id,
                client=client,
                add_unique_identifier=True,
            )

        client.create_metric_descriptor.return_value = MetricDescriptor(
            **{
                "name": None,
                "type": "custom.googleapis.com/OpenTelemetry/name",
                "display_name": "name",
                "description": "description",
                "labels": [
                    LabelDescriptor(
                        key=UNIQUE_IDENTIFIER_KEY, value_type="STRING"
                    ),
                ],
                "metric_kind": "CUMULATIVE",
                "value_type": "DOUBLE",
            }
        )

        metric = metrictestutil._generate_metric(
            "name",
            Sum(
                aggregation_temporality=AggregationTemporality.CUMULATIVE,
                is_monotonic=True,
                start_time_unix_nano=1641946015139533244,
                time_unix_nano=1641946016139533244,
                value=0.0,
            ),
            attributes=BoundedAttributes(attributes={}),
            description="description",
            unit=None,
        )

        exporter.export([metric])

        exports_1 = client.create_time_series.call_args_list[0]

        # verify the first metric started at exporter start time
        self.assertEqual(
            exports_1[0][1][0].points[0].interval.start_time.seconds,
            1641946015,
        )
        self.assertEqual(
            exports_1[0][1][0].points[0].interval.start_time.nanos, 139533244
        )

        self.assertEqual(
            exports_1[0][1][0].points[0].interval.end_time.seconds, 1641946016
        )

        metric = metrictestutil._generate_metric(
            "name",
            Sum(
                aggregation_temporality=AggregationTemporality.CUMULATIVE,
                is_monotonic=True,
                start_time_unix_nano=1641946015139533244
                + (WRITE_INTERVAL + 1) * NANOS_PER_SECOND,
                time_unix_nano=1641946016139533244
                + (WRITE_INTERVAL + 1) * NANOS_PER_SECOND,
                value=1.0,
            ),
            attributes=BoundedAttributes(attributes={}),
            description="description",
            unit=None,
        )

        exporter.export([metric])

        exports_2 = client.create_time_series.call_args_list[1]

        # 1ms ahead of end time of last export
        self.assertEqual(
            exports_2[0][1][0].points[0].interval.start_time.seconds,
            1641946015 + WRITE_INTERVAL + 1,
        )
        self.assertEqual(
            exports_2[0][1][0].points[0].interval.start_time.nanos, 139533244
        )

        self.assertEqual(
            exports_2[0][1][0].points[0].interval.end_time.seconds,
            1641946016 + WRITE_INTERVAL + 1,
        )

    def test_unique_identifier(self):
        client = mock.Mock()
        exporter1 = CloudMonitoringMetricsExporter(
            project_id=self.project_id,
            client=client,
            add_unique_identifier=True,
        )
        exporter2 = CloudMonitoringMetricsExporter(
            project_id=self.project_id,
            client=client,
            add_unique_identifier=True,
        )
        exporter1.project_name = self.project_name
        exporter2.project_name = self.project_name

        client.create_metric_descriptor.return_value = MetricDescriptor(
            **{
                "name": None,
                "type": "custom.googleapis.com/OpenTelemetry/name",
                "display_name": "name",
                "description": "description",
                "labels": [
                    LabelDescriptor(
                        key=UNIQUE_IDENTIFIER_KEY, value_type="STRING"
                    ),
                ],
                "metric_kind": "CUMULATIVE",
                "value_type": "DOUBLE",
            }
        )

        metric_record = metrictestutil._generate_sum(
            "name",
            0.0,
            attributes=BoundedAttributes(attributes={}),
            description="description",
        )
        exporter1.export([metric_record])
        exporter2.export([metric_record])

        (
            first_call,
            second_call,
        ) = client.create_metric_descriptor.call_args_list
        self.assertEqual(first_call[0][1].labels[0].key, UNIQUE_IDENTIFIER_KEY)
        self.assertEqual(
            second_call[0][1].labels[0].key, UNIQUE_IDENTIFIER_KEY
        )

        first_call, second_call = client.create_time_series.call_args_list
        self.assertNotEqual(
            first_call[0][1][0].metric.labels[UNIQUE_IDENTIFIER_KEY],
            second_call[0][1][0].metric.labels[UNIQUE_IDENTIFIER_KEY],
        )

    def test_extract_resources(self):
        exporter = CloudMonitoringMetricsExporter(project_id=self.project_id)

        self.assertIsNone(
            exporter._get_monitored_resource(Resource.get_empty())
        )
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
        expected_extract = MonitoredResource(
            type="gce_instance",
            labels={"project_id": "123", "instance_id": "host", "zone": "US"},
        )
        self.assertEqual(
            exporter._get_monitored_resource(resource), expected_extract
        )

        resource = Resource(
            attributes={
                "cloud.account.id": "123",
                "host.id": "host",
                "extra_info": "extra",
                "not_gcp_resource": "value",
                "gcp.resource_type": "gce_instance",
                "cloud.provider": "gcp",
            }
        )
        # Should throw when passed a malformed GCP resource dict
        self.assertRaises(KeyError, exporter._get_monitored_resource, resource)

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
        self.assertIsNone(exporter._get_monitored_resource(resource))

        resource = Resource(
            attributes={
                "cloud.account.id": "123",
                "host.id": "host",
                "extra_info": "extra",
                "not_gcp_resource": "value",
                "cloud.provider": "aws",
            }
        )
        self.assertIsNone(exporter._get_monitored_resource(resource))
