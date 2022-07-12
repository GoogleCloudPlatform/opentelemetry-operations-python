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
from typing import Union, Sequence
from unittest import mock

from google.api.label_pb2 import LabelDescriptor
from google.api.metric_pb2 import MetricDescriptor
from google.api.monitored_resource_pb2 import MonitoredResource
from google.cloud import monitoring_v3
from opentelemetry.exporter.cloud_monitoring import (
    MAX_BATCH_WRITE,
    NANOS_PER_SECOND,
    UNIQUE_IDENTIFIER_KEY,
    WRITE_INTERVAL,
    CloudMonitoringMetricsExporter
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import Metric
from opentelemetry.sdk.metrics.export import (
    Histogram,
    Sum,
    Gauge,
    NumberDataPoint,
    AggregationTemporality,
    MetricsData,
    ScopeMetrics,
    ResourceMetrics,
    HistogramDataPoint
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from opentelemetry.attributes import BoundedAttributes


class MockBatcher:
    def __init__(self, stateful):
        self.stateful = stateful


def mock_meter():
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
        meter=None
    ):
        self.name = name
        self.description = description
        self.meter = meter or mock_meter()


def _generate_metric(
    name, data, description=None, unit=None
) -> Metric:
    if description is None:
        description = "foo"
    if unit is None:
        unit = "s"
    return Metric(
        name=name,
        description=description,
        unit=unit,
        data=data,
    )


def _generate_sum_metric(
        name,
        value,
        attributes=None,
        description=None,
        unit=None,
        start_time_unix_nano=1641946015139533244,
        time_unix_nano=1641946016139533244,
) -> Metric:
    if attributes is None:
        attributes = BoundedAttributes(attributes={"a": 1, "b": True})
    return _generate_metric(
        name,
        Sum(
            data_points=[
                NumberDataPoint(
                    attributes=attributes,
                    start_time_unix_nano=start_time_unix_nano,
                    time_unix_nano=time_unix_nano,
                    value=value,
                )
            ],
            aggregation_temporality=AggregationTemporality.CUMULATIVE,
            is_monotonic=True,
        ),
        description=description,
        unit=unit,
    )


def _generate_gauge_metric(
        name,
        value,
        attributes=None,
        description=None,
        unit=None,
        start_time_unix_nano=1641946015139533244,
        time_unix_nano=1641946016139533244,
) -> Metric:
    if attributes is None:
        attributes = BoundedAttributes(attributes={"a": 1, "b": True})
    return _generate_metric(
        name,
        Gauge(
            data_points=[
                NumberDataPoint(
                    attributes=attributes,
                    start_time_unix_nano=start_time_unix_nano,
                    time_unix_nano=time_unix_nano,
                    value=value,
                )
            ],
        ),
        description=description,
        unit=unit,
    )


def _generate_histogram_metric(
        name,
        count: int,
        sum: Union[int, float],
        bucket_counts: Sequence[int],
        explicit_bounds: Sequence[float],
        min: float,
        max: float,
        attributes=None,
        description=None,
        unit=None,
        start_time_unix_nano=1641946015139533244,
        time_unix_nano=1641946016139533244,
) -> Metric:
    if attributes is None:
        attributes = BoundedAttributes(attributes={"a": 1, "b": True})
    return _generate_metric(
        name,
        Histogram(
            data_points=[
                HistogramDataPoint(
                    attributes=attributes,
                    start_time_unix_nano=start_time_unix_nano,
                    time_unix_nano=time_unix_nano,
                    count=count,
                    sum=sum,
                    bucket_counts=bucket_counts,
                    explicit_bounds=explicit_bounds,
                    min=min,
                    max=max
                )
            ],
            aggregation_temporality=AggregationTemporality.CUMULATIVE
        ),
        description=description,
        unit=unit,
    )


def _get_metrics_data(
        resource: Resource,
        scope: InstrumentationScope,
        metrics: Sequence[Metric]) -> MetricsData:
    return MetricsData(
        resource_metrics=[
            ResourceMetrics(
                resource=resource,
                schema_url=resource.schema_url,
                scope_metrics=[
                    ScopeMetrics(
                        scope=scope,
                        schema_url=scope.schema_url,
                        metrics=metrics,
                    )
                ]
            )
        ]
    )


def _make_create_ts_request(name, time_series) -> dict:
    return {
        "name": name,
        "time_series": time_series
    }


def _make_create_md_request(name, metrics_descriptor) -> dict:
    return {
        "name": name,
        "metric_descriptor": metrics_descriptor
    }


_scope = InstrumentationScope(
            name="first_name",
            version="first_version",
            schema_url="instrumentation_scope_schema_url",
        )


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

    def test_batch_write(self):
        client = mock.Mock()
        exporter = CloudMonitoringMetricsExporter(
            project_id=self.project_id, client=client
        )
        exporter.project_name = self.project_name
        exporter._batch_write(range(2 * MAX_BATCH_WRITE + 1))
        calls = [
            mock.call(
                request=_make_create_ts_request(
                    self.project_name,
                    range(MAX_BATCH_WRITE)
                )
            ),
            mock.call(
                request=_make_create_ts_request(
                    self.project_name,
                    range(MAX_BATCH_WRITE, 2 * MAX_BATCH_WRITE),
                )
            ),
            mock.call(
                request=_make_create_ts_request(
                    self.project_name,
                    range(2 * MAX_BATCH_WRITE, 2 * MAX_BATCH_WRITE + 1),
                )
            )
        ]
        client.create_time_series.assert_has_calls(calls)

        exporter._batch_write(range(MAX_BATCH_WRITE))
        calls += [mock.call(request=_make_create_ts_request(self.project_name, range(MAX_BATCH_WRITE)))]
        client.create_time_series.assert_has_calls(calls)

        exporter._batch_write(range(MAX_BATCH_WRITE - 1))
        calls += [mock.call(request=_make_create_ts_request(self.project_name, range(MAX_BATCH_WRITE - 1)))]
        client.create_time_series.assert_has_calls(calls)

    def test_get_metric_descriptor(self):
        client = mock.Mock()
        exporter = CloudMonitoringMetricsExporter(
            project_id=self.project_id, client=client
        )
        exporter.project_name = self.project_name

        self.assertIsNone(
            exporter._get_metric_descriptor(
                Metric(
                    "",
                    None,
                    None,
                    Sum(
                        data_points=[],
                        aggregation_temporality=AggregationTemporality.CUMULATIVE,
                        is_monotonic=True
                    )
                )
            )
        )

        metric = _generate_sum_metric(
            name="name",
            value=1,
            description="description",
            attributes={"label1": "label1_value"}
        )
        metric_descriptor = exporter._get_metric_descriptor(metric)
        client.create_metric_descriptor.assert_called_with(
            request=_make_create_md_request(
                self.project_name,
                MetricDescriptor(
                    **{
                        "type": "custom.googleapis.com/OpenTelemetry/name",
                        "display_name": "name",
                        "description": "description",
                        "labels": [
                            LabelDescriptor(key="label1", value_type="STRING")
                        ],
                        "metric_kind": "CUMULATIVE",
                        "value_type": "INT64",
                    }
                )
            )
        )

        # Getting a cached metric descriptor shouldn't use another call
        cached_metric_descriptor = exporter._get_metric_descriptor(metric)
        self.assertEqual(client.create_metric_descriptor.call_count, 1)
        self.assertEqual(metric_descriptor, cached_metric_descriptor)

        # Drop labels with values that aren't string, int or bool
        metric2 = _generate_sum_metric(
            name="name2",
            description="description",
            attributes={
                "label1":  "value1",
                "label2":  dict(),
                "label3":  3,
                "label4":  False,
            },
            value=1.0
        )
        exporter._get_metric_descriptor(
            metric2
        )
        client.create_metric_descriptor.assert_called_with(
            request=_make_create_md_request(
                self.project_name,
                MetricDescriptor(
                    **{
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
                )
            )
        )

    def test_get_value_observer_metric_descriptor(self):
        client = mock.Mock()
        exporter = CloudMonitoringMetricsExporter(
            project_id=self.project_id, client=client
        )
        exporter.project_name = self.project_name
        metric = _generate_gauge_metric(
            name="name",
            description="description",
            unit=None,
            value=1
        )
        exporter._get_metric_descriptor(metric)
        client.create_metric_descriptor.assert_called_with(
            request=_make_create_md_request(
                self.project_name,
                MetricDescriptor(
                    **{
                        "type": "custom.googleapis.com/OpenTelemetry/name",
                        "display_name": "name",
                        "description": "description",
                        "labels": [],
                        "metric_kind": "GAUGE",
                        "value_type": "INT64",
                    }
                )
            )
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
        calls = []

        exporter.export(
            MetricsData(
                resource_metrics=[
                    ResourceMetrics(
                        resource=Resource(
                            attributes={"a": 1, "b": False},
                            schema_url="resource_schema_url",
                        ),
                        scope_metrics=[
                            ScopeMetrics(
                                scope=InstrumentationScope(
                                    name="first_name",
                                    version="first_version",
                                    schema_url="insrumentation_scope_schema_url",
                                ),
                                metrics=[
                                    Metric(
                                        "",
                                        None,
                                        None,
                                        Sum(
                                            data_points=[],
                                            aggregation_temporality=AggregationTemporality.CUMULATIVE,
                                            is_monotonic=True
                                        )
                                    )
                                ],
                                schema_url="instrumentation_scope_schema_url",
                            )
                        ],
                        schema_url="resource_schema_url",
                    )
                ]
            )
        )
        client.create_time_series.assert_not_called()

        client.create_metric_descriptor.return_value = MetricDescriptor(
            **{
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

        resource = Resource.create(
            attributes={
                "cloud.account.id": 123,
                "host.id": "host",
                "cloud.zone": "US",
                "cloud.provider": "gcp",
                "extra_info": "extra",
                "gcp.resource_type": "gce_instance",
                "not_gcp_resource": "value",
            },
            schema_url="resource_schema_url",
        )
        metrics = [
            _generate_sum_metric(
                name="name",
                value=1,
                attributes={
                    "label1": "value1",
                    "label2": 1,
                },
                start_time_unix_nano=1 * NANOS_PER_SECOND,
                time_unix_nano=(WRITE_INTERVAL + 1) * NANOS_PER_SECOND
            ),
            _generate_sum_metric(
                name="name",
                value=1,
                attributes={
                    "label1": "value2",
                    "label2": 2,
                },
                start_time_unix_nano=1 * NANOS_PER_SECOND,
                time_unix_nano=(WRITE_INTERVAL + 1) * NANOS_PER_SECOND
            )
        ]
        metrics_data = _get_metrics_data(
                resource=resource,
                scope=_scope,
                metrics=metrics
            )
        exporter.export(metrics_data)

        expected_resource = MonitoredResource(
            type="gce_instance",
            labels={"project_id": "123", "instance_id": "host", "zone": "US"},
        )

        series1 = monitoring_v3.TimeSeries(resource=expected_resource)
        series1.metric_kind = MetricDescriptor.MetricKind.CUMULATIVE
        series1.metric.type = "custom.googleapis.com/OpenTelemetry/name"
        series1.metric.labels["label1"] = "value1"
        series1.metric.labels["label2"] = "1"
        point = monitoring_v3.Point()
        point.value.int64_value = 1
        point.interval = monitoring_v3.TimeInterval({
            "end_time": {
                "seconds": WRITE_INTERVAL + 1,
                "nanos": 0
            },
            "start_time": {
                "seconds": 1,
                "nanos": 0
            }
        })
        series1.points = [point]

        series2 = monitoring_v3.TimeSeries(resource=expected_resource)
        series2.metric_kind = MetricDescriptor.MetricKind.CUMULATIVE
        series2.metric.type = "custom.googleapis.com/OpenTelemetry/name"
        series2.metric.labels["label1"] = "value2"
        series2.metric.labels["label2"] = "2"
        point = monitoring_v3.Point()
        point.value.int64_value = 1
        point.interval = monitoring_v3.TimeInterval({
            "end_time": {
                "seconds": WRITE_INTERVAL + 1,
                "nanos": 0
            },
            "start_time": {
                "seconds": 1,
                "nanos": 0
            }
        })
        series2.points = [point]

        calls.append(
            mock.call(
                request=_make_create_ts_request(
                    name=self.project_name,
                    time_series=[series1, series2]
                )
            )
        )
        client.create_time_series.assert_has_calls(calls)

        # Attempting to export too soon after another export with the exact
        # same labels leads to it being dropped

        # exporter.export(
        #     _get_metrics_data(
        #         resource=Resource.get_empty(),
        #         scope=_scope,
        #         metrics=metrics
        #     )
        # )
        # self.assertEqual(client.create_time_series.call_count, 1)

        exporter.export(
            _get_metrics_data(
                resource=Resource.get_empty(),
                scope=_scope,
                metrics=[
                    _generate_sum_metric(
                        name="name",
                        value=2,
                        attributes={
                            "label1": "changed_label",
                            "label2": 2,
                        },
                        start_time_unix_nano=1 * NANOS_PER_SECOND,
                        time_unix_nano=(WRITE_INTERVAL + 2) * NANOS_PER_SECOND
                    )
                ]
            )
        )
        series3 = monitoring_v3.TimeSeries()
        series3.metric_kind = MetricDescriptor.MetricKind.CUMULATIVE
        series3.metric.type = "custom.googleapis.com/OpenTelemetry/name"
        series3.metric.labels["label1"] = "changed_label"
        series3.metric.labels["label2"] = "2"
        point = monitoring_v3.Point()
        point.value.int64_value = 2
        point.interval = monitoring_v3.TimeInterval({
            "end_time": {
                "seconds": WRITE_INTERVAL + 2,
                "nanos": 0
            },
            "start_time": {
                "seconds": 1,
                "nanos": 0
            }
        })
        series3.points = [point]

        calls.append(mock.call(request=_make_create_ts_request(self.project_name, [series3])))
        client.create_time_series.assert_has_calls(calls)

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
                "type": "custom.googleapis.com/OpenTelemetry/name",
                "display_name": "name",
                "description": "description",
                "labels": [],
                "metric_kind": "GAUGE",
                "value_type": "INT64",
            }
        )

        exporter.export(
            _get_metrics_data(
                resource=Resource.get_empty(),
                scope=_scope,
                metrics=[
                    _generate_gauge_metric(
                        name="name",
                        value=5,
                        start_time_unix_nano=(WRITE_INTERVAL + 1) * NANOS_PER_SECOND,
                        time_unix_nano=(WRITE_INTERVAL + 1) * NANOS_PER_SECOND,
                        attributes={}
                    )
                ]
            )
        )

        series = monitoring_v3.TimeSeries()
        series.metric_kind = MetricDescriptor.MetricKind.GAUGE
        series.metric.type = "custom.googleapis.com/OpenTelemetry/name"
        point = monitoring_v3.Point()
        point.value.int64_value = 5
        point.interval = monitoring_v3.TimeInterval({
            "end_time": {
                "seconds": WRITE_INTERVAL + 1,
                "nanos": 0
            },
            "start_time": {
                "seconds": WRITE_INTERVAL + 1,
                "nanos": 0
            }
        })
        series.points = [point]
        
        client.create_time_series.assert_has_calls(
            [mock.call(request=_make_create_ts_request(self.project_name, [series]))]
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
                "type": "custom.googleapis.com/OpenTelemetry/name",
                "display_name": "name",
                "description": "description",
                "labels": [],
                "metric_kind": "CUMULATIVE",
                "value_type": "DISTRIBUTION",
            }
        )

        exporter.export(
            _get_metrics_data(
                resource=Resource.get_empty(),
                scope=_scope,
                metrics=[
                    _generate_histogram_metric(
                        attributes={},
                        name="name",
                        count=5,
                        sum=67,
                        bucket_counts=[1, 4],
                        explicit_bounds=[10.0, 20.0],
                        max=18.0,
                        min=8.0,
                        start_time_unix_nano=1 * NANOS_PER_SECOND,
                        time_unix_nano=(WRITE_INTERVAL + 1) * NANOS_PER_SECOND
                    )
                ]
            )
        )

        series = monitoring_v3.TimeSeries()
        series.metric_kind = MetricDescriptor.MetricKind.CUMULATIVE
        series.metric.type = "custom.googleapis.com/OpenTelemetry/name"
        point = {
            "interval": {
                "start_time": {"seconds": 1},
                "end_time": {"seconds": 11},
            },
            "value": {
                "distribution_value": {
                    "count": 5,
                    "bucket_options": {
                        "explicit_buckets": {"bounds": [10.0, 20.0]}
                    },
                    "bucket_counts": [1, 4],
                }
            },
        }
        series.points = [monitoring_v3.Point(point)]
        client.create_time_series.assert_has_calls(
            [mock.call(request=_make_create_ts_request(self.project_name, [series]))]
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

        metric_data = _get_metrics_data(
            resource=Resource.get_empty(),
            scope=_scope,
            metrics=[
                _generate_sum_metric(
                    "name",
                    value=1
                )
            ]
        )
        exporter1.export(metric_data)
        exporter2.export(metric_data)

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
