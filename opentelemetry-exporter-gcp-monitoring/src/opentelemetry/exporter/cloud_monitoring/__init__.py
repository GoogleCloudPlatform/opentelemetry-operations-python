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
import threading
from typing import Optional, Sequence

import google.auth
from google.api.distribution_pb2 import Distribution
from google.api.label_pb2 import LabelDescriptor
from google.api.metric_pb2 import MetricDescriptor
from google.api.monitored_resource_pb2 import MonitoredResource
from google.cloud.monitoring_v3 import MetricServiceClient
from google.cloud.monitoring_v3.proto.metric_pb2 import TimeSeries
from opentelemetry.exporter.cloud_monitoring._time import time_ns
from opentelemetry.sdk._metrics import UpDownCounter
from opentelemetry.sdk._metrics.export import (
    Metric,
    MetricExporter,
    MetricExportResult,
)
from opentelemetry.sdk._metrics.point import (
    Histogram,
    Sum,
    Gauge,
)
from opentelemetry.sdk.resources import Resource

logger = logging.getLogger(__name__)
MAX_BATCH_WRITE = 200
WRITE_INTERVAL = 10
UNIQUE_IDENTIFIER_KEY = "opentelemetry_id"
NANOS_PER_SECOND = 10**9

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
        self.project_name = self.client.project_path(self.project_id)
        self._metric_descriptors = {}
        self._last_updated = {}
        self.unique_identifier = None
        if add_unique_identifier:
            self.unique_identifier = "{:08x}".format(
                random.randint(0, 16**8)
            )

        (
            self._exporter_start_time_seconds,
            self._exporter_start_time_nanos,
        ) = divmod(time_ns(), NANOS_PER_SECOND)
        self.lock = threading.Lock()

    @staticmethod
    def _get_monitored_resource(
        resource: Resource,
    ) -> Optional[MonitoredResource]:
        """Add Google resource specific information (e.g. instance id, region).

        See
        https://cloud.google.com/monitoring/custom-metrics/creating-metrics#custom-metric-resources
        for supported types
        Args:
            series: ProtoBuf TimeSeries
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

    def _batch_write(self, series: TimeSeries) -> None:
        """Cloud Monitoring allows writing up to 200 time series at once

        :param series: ProtoBuf TimeSeries
        :return:
        """
        write_ind = 0
        while write_ind < len(series):
            self.client.create_time_series(
                self.project_name,
                series[write_ind : write_ind + MAX_BATCH_WRITE],
            )
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
        self.lock.acquire()
        descriptor_type = "custom.googleapis.com/OpenTelemetry/{}".format(
            metric.name
        )
        if descriptor_type in self._metric_descriptors:
            self.lock.release()
            return self._metric_descriptors[descriptor_type]

        descriptor = {  # type: ignore[var-annotated] # TODO #56
            "name": None,
            "type": descriptor_type,
            "display_name": metric.name,
            "description": metric.description,
            "labels": [],
        }
        for key, value in list(metric.attributes.items()):
            if isinstance(value, str):
                descriptor["labels"].append(  # type: ignore[union-attr] # TODO #56
                    LabelDescriptor(key=key, value_type="STRING")
                )
            elif isinstance(value, bool):
                descriptor["labels"].append(  # type: ignore[union-attr] # TODO #56
                    LabelDescriptor(key=key, value_type="BOOL")
                )
            elif isinstance(value, int):
                descriptor["labels"].append(  # type: ignore[union-attr] # TODO #56
                    LabelDescriptor(key=key, value_type="INT64")
                )
            else:
                logger.warning(
                    "Label value %s is not a string, bool or integer, ignoring it",
                    value,
                )

        if self.unique_identifier:
            descriptor["labels"].append(  # type: ignore[union-attr] # TODO #56
                LabelDescriptor(key=UNIQUE_IDENTIFIER_KEY, value_type="STRING")
            )

        # SumAggregation is best represented as a cumulative, but it can't be
        # represented that way if it can decrement. So we need to make sure
        # that the instrument is not an UpDownCounter
        if isinstance(metric.point, Sum) and not isinstance(
            metric.point, UpDownCounter
        ):
            descriptor["metric_kind"] = MetricDescriptor.MetricKind.CUMULATIVE
        elif isinstance(metric.point, Gauge):
            descriptor["metric_kind"] = MetricDescriptor.MetricKind.GAUGE
        elif isinstance(metric.point, Histogram):
            descriptor["metric_kind"] = MetricDescriptor.MetricKind.CUMULATIVE
        else:
            logger.warning(
                "Unsupported instrument/aggregator combo, types %s and %s, ignoring it",
                type(metric).__name__,
                type(metric.point).__name__,
            )
            self.lock.release()
            return None

        if isinstance(metric.point, Histogram):
            descriptor["value_type"] = MetricDescriptor.ValueType.DISTRIBUTION
        elif isinstance(metric.point.value, int):
            descriptor["value_type"] = MetricDescriptor.ValueType.INT64
        elif isinstance(metric.point.value, float):
            descriptor["value_type"] = MetricDescriptor.ValueType.DOUBLE

        proto_descriptor = MetricDescriptor(**descriptor)
        try:
            descriptor = self.client.create_metric_descriptor(
                self.project_name, proto_descriptor
            )
        # pylint: disable=broad-except
        except Exception as ex:
            logger.error(
                "Failed to create metric descriptor %s",
                proto_descriptor,
                exc_info=ex,
            )
            self.lock.release()
            return None
        self._metric_descriptors[descriptor_type] = descriptor
        self.lock.release()
        return descriptor

    def _set_start_end_times(
        self, point_dict, metric: Metric, metric_descriptor
    ):
        updated_key = (
            metric_descriptor.type,
            frozenset(metric.attributes.items()),
        )
        start_time_unix_nano = (
            metric.point.time_unix_nano
            if isinstance(metric.point, Gauge)
            else metric.point.start_time_unix_nano
        )
        start_seconds, start_nanos = divmod(
            start_time_unix_nano, NANOS_PER_SECOND
        )
        point_dict["interval"]["start_time"] = {
            "seconds": start_seconds,
            "nanos": start_nanos,
        }

        end_time_unix_nano = metric.point.time_unix_nano
        end_seconds, end_nanos = divmod(end_time_unix_nano, NANOS_PER_SECOND)
        point_dict["interval"]["end_time"] = {
            "seconds": end_seconds,
            "nanos": end_nanos,
        }
        self._last_updated[updated_key] = end_time_unix_nano

    def export(self, metrics: Sequence[Metric]) -> "MetricExportResult":
        all_series = []
        for metric in metrics:
            metric_descriptor = self._get_metric_descriptor(metric)
            if not metric_descriptor:
                continue
            series = TimeSeries(
                resource=self._get_monitored_resource(metric.resource),
                # TODO: remove
                # https://github.com/GoogleCloudPlatform/opentelemetry-operations-python/issues/84
                metric_kind=metric_descriptor.metric_kind,
            )
            series.metric.type = metric_descriptor.type
            for key, value in list(metric.attributes.items()):
                series.metric.labels[key] = str(value)

            if self.unique_identifier:
                series.metric.labels[
                    UNIQUE_IDENTIFIER_KEY
                ] = self.unique_identifier

            point_dict = {"interval": {}}  # type: ignore[var-annotated] # TODO #56

            if isinstance(metric.point, Histogram):
                bucket_bounds = list(metric.point.explicit_bounds)
                bucket_values = list(metric.point.bucket_counts)
                point_dict["value"] = {
                    "distribution_value": Distribution(
                        count=sum(bucket_values),
                        bucket_counts=bucket_values,
                        bucket_options={
                            "explicit_buckets": {"bounds": bucket_bounds}
                        },
                    )
                }
            else:
                if isinstance(metric.point, Sum):
                    data_point = metric.point.value
                elif isinstance(metric.point, Gauge):
                    data_point = metric.point.value

                if isinstance(data_point, int):
                    point_dict["value"] = {"int64_value": data_point}
                elif isinstance(data_point, float):
                    point_dict["value"] = {"double_value": data_point}

            seconds = metric.point.time_unix_nano // NANOS_PER_SECOND

            # Cloud Monitoring API allows, for any combination of labels and
            # metric name, one update per WRITE_INTERVAL seconds
            updated_key = (
                metric_descriptor.type,
                frozenset(metric.attributes.items()),
            )
            last_updated_time = self._last_updated.get(updated_key, 0)
            last_updated_time_seconds = last_updated_time // NANOS_PER_SECOND
            if seconds <= last_updated_time_seconds + WRITE_INTERVAL:
                continue

            self._set_start_end_times(point_dict, metric, metric_descriptor)
            series.points.add(**point_dict)
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

    def shutdown(self) -> None:
        pass
