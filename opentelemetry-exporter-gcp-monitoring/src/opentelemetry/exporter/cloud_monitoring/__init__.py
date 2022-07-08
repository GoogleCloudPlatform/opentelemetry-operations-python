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
from google.cloud.monitoring_v3 import TimeSeries, Point
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
        return MonitoredResource(
            type=resource_type,
            labels={
                gcp_label: str(resource_attributes[ot_label])
                for ot_label, gcp_label in OT_RESOURCE_LABEL_TO_GCP[
                    resource_type
                ].items()
            },
        )

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

        descriptor = {  # type: ignore[var-annotated] # TODO #56
            "name": None,
            "type": descriptor_type,
            "display_name": metric.name,
            "description": metric.description,
            "labels": []
        }

        if self.unique_identifier:
            descriptor["labels"].append(  # type: ignore[union-attr] # TODO #56
                LabelDescriptor(key=UNIQUE_IDENTIFIER_KEY, value_type="STRING")
            )

        for number_data_point in metric.data.data_points:
            for key, value in number_data_point.attributes.items():
                if isinstance(value, bool):
                    descriptor["labels"].append(
                        LabelDescriptor(key=key, value_type="BOOL")
                    )
                elif isinstance(value, int):
                    descriptor["labels"].append(
                        LabelDescriptor(key=key, value_type="INT64")
                    )
                else:
                    descriptor["labels"].append(
                        LabelDescriptor(key=key, value="STRING")
                    )

        if isinstance(metric.data, Sum):
            descriptor["metric_kind"] = MetricDescriptor.MetricKind.CUMULATIVE
        elif isinstance(metric.data, Gauge):
            descriptor["metric_kind"] = MetricDescriptor.MetricKind.GAUGE
        elif isinstance(metric.data, Histogram):
            descriptor["metric_kind"] = MetricDescriptor.MetricKind.CUMULATIVE
        else:
            logger.warning(
                "Unsupported instrument/aggregator combo, types %s, ignoring it",
                type(metric).__name__
            )
            return None

        if isinstance(metric.data, Histogram):
            descriptor["value_type"] = MetricDescriptor.ValueType.DISTRIBUTION
        elif metric.data.data_points[0].value == int:
            descriptor["value_type"] = MetricDescriptor.ValueType.INT64
        elif metric.data.data_points[0].value == float:
            descriptor["value_type"] = MetricDescriptor.ValueType.DOUBLE

        proto_descriptor = MetricDescriptor(**descriptor)
        try:
            descriptor = self.client.create_metric_descriptor({
                "name": self.project_name,
                "metric_descriptor": proto_descriptor
            })
        # pylint: disable=broad-except
        except Exception as ex:
            logger.error(
                "Failed to create metric descriptor %s",
                proto_descriptor,
                exc_info=ex,
            )
            return None
        self._metric_descriptors[descriptor_type] = descriptor
        return descriptor

    def _set_start_end_times(self, point_dict, metric: Metric, metric_descriptor):
        last_data_point = metric.data.data_points[-1]
        updated_key = (metric_descriptor.type, frozenset(last_data_point.attributes.items()))
        seconds, nanos = last_data_point.start_time_unix_nano, last_data_point.time_unix_nano

        if (
                metric_descriptor.metric_kind
                == MetricDescriptor.MetricKind.CUMULATIVE
        ):
            if updated_key not in self._last_updated:
                # The aggregation has not reset since the exporter
                # has started up, so that is the start time
                point_dict["interval"]["start_time"] = {
                    "seconds": self._exporter_start_time_seconds,
                    "nanos": self._exporter_start_time_nanos,
                }
            else:
                # The aggregation reset the last time it was exported
                # Add 1ms to guarantee there is no overlap from the previous export
                # (see https://cloud.google.com/monitoring/api/ref_v3/rpc/google.monitoring.v3#timeinterval)
                (start_seconds, start_nanos,) = divmod(
                    self._last_updated[updated_key] + int(1e6),
                    NANOS_PER_SECOND,
                )
                point_dict["interval"]["start_time"] = {
                    "seconds": start_seconds,
                    "nanos": start_nanos,
                }
        else:
            point_dict["interval"]["start_time"] = {
                "seconds": seconds,
                "nanos": nanos,
            }

        self._last_updated[
            updated_key
        ] = {
            "seconds": seconds,
            "nanos": nanos,
        }
        point_dict["interval"]["end_time"] = {
            "seconds": seconds,
            "nanos": nanos,
        }

    def _metric_to_timeseries(
            self,
            metric: Metric,
            metrics_descriptor: MetricDescriptor,
            resource: Optional[MonitoredResource]
    ) -> TimeSeries:
        labels = {}
        for attr in [pt.attributes for pt in metric.data.data_points]:
            for k, v in attr.items():
                labels[k] = str(v)
        point_dict = {}
        self._set_start_end_times(
            point_dict=point_dict,
            metric=metric,
            metric_descriptor=metrics_descriptor
        )
        if isinstance(metric.data, Sum):
            point_dict['value'] = sum([pt.value for pt in metric.data.data_points])
        elif isinstance(metric.data, Gauge):
            point_dict['value'] = [pt.value for pt in metric.data.data_points][-1]
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
        series.metric.labels = labels
        series.resource = resource
        series.metric_kind = metrics_descriptor.metric_kind,
        series.value_type = metrics_descriptor.value_type,
        series.points = [Point(**point_dict)],
        series.unit = metrics_descriptor.unit

        return series

    def export(self, metrics_data: MetricsData, **kwargs) -> MetricExportResult:
        all_series = []

        for resource_metric in metrics_data.resource_metrics:
            resource = self._get_monitored_resource(resource_metric.resource),
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
                seconds = metric.data.data_points[-1].time_unix_nano
            # Cloud Monitoring API allows, for any combination of labels and
            # metric name, one update per WRITE_INTERVAL seconds
                updated_key = (
                    metric_descriptor.type,
                    frozenset(series.metric.labels),
                )
                last_updated_time = self._last_updated.get(updated_key, 0)
                last_updated_time_seconds = last_updated_time // NANOS_PER_SECOND
                if seconds <= last_updated_time_seconds + WRITE_INTERVAL:
                    continue
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
