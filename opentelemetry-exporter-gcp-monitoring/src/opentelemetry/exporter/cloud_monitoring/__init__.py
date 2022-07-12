# Copyright 2021 Google LLC
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
import random
from typing import Optional, Sequence

import google.auth
from google.api.distribution_pb2 import Distribution
from google.api.label_pb2 import LabelDescriptor
from google.api.metric_pb2 import MetricDescriptor
from google.api.monitored_resource_pb2 import MonitoredResource
from google.cloud.monitoring_v3 import MetricServiceClient
from google.cloud.monitoring_v3 import TimeSeries, Point, TimeInterval
from opentelemetry.exporter.cloud_monitoring._time import time_ns
from opentelemetry.sdk.metrics.export import (
    MetricExporter,
    MetricExportResult,
    Metric
)
from opentelemetry.sdk.metrics.export import (
    Histogram,
    Sum,
    Gauge,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.metrics._internal.point import MetricsData

logger = logging.getLogger(__name__)
MAX_BATCH_WRITE = 200
WRITE_INTERVAL = 10
UNIQUE_IDENTIFIER_KEY = "opentelemetry_id"
NANOS_PER_SECOND = 10 ** 9

OT_RESOURCE_LABEL_TO_GCP = {
    "gce_instance": {
        "host.id": "instance_id",
        "cloud.account.id": "project_id",
        "cloud.zone": "zone",
    },
    "gke_container": {
        "k8s.cluster.name": "cluster_name",
        "k8s.namespace.name": "namespace_id",
        "k8s.pod.name": "pod_id",
        "host.id": "instance_id",
        "container.name": "container_name",
        "cloud.account.id": "project_id",
        "cloud.zone": "zone",
    },
}


# pylint is unable to resolve members of protobuf objects
# pylint: disable=no-member
# pylint: disable=too-many-branches
# pylint: disable=too-many-locals
class CloudMonitoringMetricsExporter(MetricExporter):
    """Implementation of Metrics Exporter to Google Cloud Monitoring
        You can manually pass in project_id and client, or else the
        Exporter will take that information from Application Default
        Credentials.
    Args:
        project_id: project id of your Google Cloud project.
        client: Client to upload metrics to Google Cloud Monitoring.
        add_unique_identifier: Add an identifier to each exporter metric. This
            must be used when there exist two (or more) exporters that may
            export to the same metric name within WRITE_INTERVAL seconds of
            each other.
    """

    def __init__(
            self, project_id=None, client=None, add_unique_identifier=False
    ):
        self.client = client or MetricServiceClient()
        if not project_id:
            _, self.project_id = google.auth.default()
        else:
            self.project_id = project_id
        self.project_name = f"projects/{project_id}"
        self._metric_descriptors = {}
        self._last_updated = {}
        self.unique_identifier = None
        if add_unique_identifier:
            self.unique_identifier = "{:08x}".format(
                random.randint(0, 16 ** 8)
            )

        (
            self._exporter_start_time_seconds,
            self._exporter_start_time_nanos,
        ) = divmod(time_ns(), NANOS_PER_SECOND)

    @staticmethod
    def _get_monitored_resource(
            resource: Resource,
    ) -> Optional[MonitoredResource]:
        """Add Google resource specific information (e.g. instance id, region).
        See
        https://cloud.google.com/monitoring/custom-metrics/creating-metrics#custom-metric-resources
        for supported types
        Args:
            resource: open-telemetry resource
        """
        resource_attributes = resource.attributes
        if resource_attributes.get("cloud.provider") != "gcp":
            return None
        resource_type = resource_attributes["gcp.resource_type"]
        if (
                not isinstance(resource_type, str)
                or resource_type not in OT_RESOURCE_LABEL_TO_GCP
        ):
            return None
        resource = MonitoredResource()
        resource.type = resource_type
        for ot_label, gcp_label in OT_RESOURCE_LABEL_TO_GCP[resource_type].items():
            resource.labels[gcp_label] = str(resource_attributes[ot_label])
        return resource

    def _batch_write(self, series: Sequence[TimeSeries]) -> None:
        """Cloud Monitoring allows writing up to 200 time series at once
        :param series: ProtoBuf TimeSeries
        :return:
        """
        write_ind = 0
        while write_ind < len(series):
            self.client.create_time_series(request={
                "name": self.project_name,
                "time_series": series[write_ind:write_ind + MAX_BATCH_WRITE],
            })
            write_ind += MAX_BATCH_WRITE

    def _get_metric_descriptor(
            self, metric: Metric
    ) -> Optional[MetricDescriptor]:
        """We can map Metric to MetricDescriptor using Metric.name or
        MetricDescriptor.type. We create the MetricDescriptor if it doesn't
        exist already and cache it. Note that recreating MetricDescriptors is
        a no-op if it already exists.
        :param metric:
        :return:
        """
        descriptor_type = "custom.googleapis.com/OpenTelemetry/{}".format(
            metric.name
        )
        if descriptor_type in self._metric_descriptors:
            return self._metric_descriptors[descriptor_type]

        proto_descriptor = MetricDescriptor()
        proto_descriptor.type = descriptor_type
        proto_descriptor.display_name = metric.name
        if metric.description:
            proto_descriptor.description = metric.description

        if self.unique_identifier:
            labels = LabelDescriptor()
            labels.key = UNIQUE_IDENTIFIER_KEY
            labels.value_type = LabelDescriptor.ValueType.STRING
            proto_descriptor.labels.append(labels)

        for number_data_point in metric.data.data_points:
            for key, value in number_data_point.attributes.items():
                if isinstance(value, bool):
                    labels = LabelDescriptor()
                    labels.key = key
                    labels.value_type = LabelDescriptor.ValueType.BOOL
                    proto_descriptor.labels.append(labels)

                elif isinstance(value, int):
                    labels = LabelDescriptor()
                    labels.key = key
                    labels.value_type = LabelDescriptor.ValueType.INT64
                    proto_descriptor.labels.append(labels)

                elif isinstance(value, str):
                    labels = LabelDescriptor()
                    labels.key = key
                    labels.value_type = LabelDescriptor.ValueType.STRING
                    proto_descriptor.labels.append(labels)

        if isinstance(metric.data, Sum):
            proto_descriptor.metric_kind = MetricDescriptor.MetricKind.CUMULATIVE
        elif isinstance(metric.data, Gauge):
            proto_descriptor.metric_kind = MetricDescriptor.MetricKind.GAUGE
        elif isinstance(metric.data, Histogram):
            proto_descriptor.metric_kind = MetricDescriptor.MetricKind.CUMULATIVE
        else:
            logger.warning(
                "Unsupported instrument/aggregator combo, types %s, ignoring it",
                type(metric).__name__
            )
            return None

        if isinstance(metric.data, Histogram):
            proto_descriptor.value_type = MetricDescriptor.ValueType.DISTRIBUTION
        elif not metric.data.data_points:
            logger.warning("No data point in Metric")
            return None
        elif isinstance(metric.data.data_points[0].value, int):
            proto_descriptor.value_type = MetricDescriptor.ValueType.INT64
        elif isinstance(metric.data.data_points[0].value, float):
            proto_descriptor.value_type = MetricDescriptor.ValueType.DOUBLE

        try:
            proto_descriptor = self.client.create_metric_descriptor(
                request={
                    "name": self.project_name,
                    "metric_descriptor": proto_descriptor
                }
            )
        # pylint: disable=broad-except
        except Exception as ex:
            logger.error(
                "Failed to create metric descriptor %s",
                proto_descriptor,
                exc_info=ex,
            )
            return None
        self._metric_descriptors[descriptor_type] = proto_descriptor
        return proto_descriptor

    @staticmethod
    def _metric_to_timeseries(
            metric: Metric,
            metrics_descriptor: MetricDescriptor,
            resource: Optional[MonitoredResource]
    ) -> TimeSeries:
        labels = {}
        for attr in [pt.attributes for pt in metric.data.data_points]:
            for k, v in attr.items():
                labels[k] = str(v)
        point_dict = {}
        if metric.data.data_points[-1].start_time_unix_nano:
            start_seconds, start_nanos = divmod(
                metric.data.data_points[-1].start_time_unix_nano,
                NANOS_PER_SECOND
            )
            end_seconds, end_nanos = divmod(
                metric.data.data_points[-1].time_unix_nano,
                NANOS_PER_SECOND
            )
            point_dict['interval'] = TimeInterval({
                "start_time": {
                    'seconds': start_seconds,
                    'nanos': start_nanos
                },
                "end_time": {
                    'seconds': end_seconds,
                    'nanos': end_nanos
                }
            })
        else:
            end_seconds, end_nanos = divmod(
                metric.data.data_points[-1].time_unix_nano,
                NANOS_PER_SECOND
            )
            point_dict['interval'] = TimeInterval({
                "end_time": {
                    'seconds': end_seconds,
                    'nanos': end_nanos
                }
            })
        if isinstance(metric.data, Sum):
            result = sum([pt.value for pt in metric.data.data_points])
            if isinstance(result, int):
                point_dict['value'] = {"int64_value": result}
            elif isinstance(result, float):
                point_dict['value'] = {"double_value": result}
        elif isinstance(metric.data, Gauge):
            v = metric.data.data_points[-1].value
            if isinstance(v, int):
                point_dict['value'] = {"int64_value": v}
            elif isinstance(v, float):
                point_dict['value'] = {"double_value": v}
        elif isinstance(metric.data, Histogram):
            point_dict['value'] = {
                "distribution_value": Distribution(
                    count=metric.data.data_points[-1].count,
                    bucket_counts=metric.data.data_points[-1].bucket_counts,
                    bucket_options={
                        "explicit_buckets": {
                            # don't put in > bucket
                            "bounds": metric.data.data_points[-1].explicit_bounds
                        }
                    },
                )
            }
        else:
            pass
        series = TimeSeries()
        series.metric.type = metrics_descriptor.type
        for k, v in labels.items():
            series.metric.labels[k] = v
        if resource:
            series.resource.type = resource.type
            for k in resource.labels:
                series.resource.labels[k] = resource.labels[k]

        series.metric_kind = metrics_descriptor.metric_kind
        series.points = [Point(point_dict)]
        series.unit = metrics_descriptor.unit

        return series

    def export(self, metrics_data: MetricsData, **kwargs) -> MetricExportResult:
        all_series = []

        for resource_metric in metrics_data.resource_metrics:
            resource = self._get_monitored_resource(resource_metric.resource)
            for metric in (m
                           for scope_metric in resource_metric.scope_metrics
                           for m in scope_metric.metrics):
                metric_descriptor = self._get_metric_descriptor(metric)
                if not metric_descriptor:
                    continue

                series = self._metric_to_timeseries(
                    metric=metric,
                    metrics_descriptor=metric_descriptor,
                    resource=resource
                )
                all_series.append(series)
        try:
            self._batch_write(all_series)
        # pylint: disable=broad-except
        except Exception as ex:
            logger.error(
                "Error while writing to Cloud Monitoring", exc_info=ex
            )
            return MetricExportResult.FAILURE
        return MetricExportResult.SUCCESS

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        pass
