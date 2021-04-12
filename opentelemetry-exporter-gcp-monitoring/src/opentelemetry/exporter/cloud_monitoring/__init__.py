# Copyright 2021 Google
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
from google.cloud.monitoring_v3.proto.metric_pb2 import TimeSeries
from opentelemetry.exporter.cloud_monitoring._time import time_ns
from opentelemetry.sdk.metrics import UpDownCounter
from opentelemetry.sdk.metrics.export import (
    ExportRecord,
    MetricsExporter,
    MetricsExportResult,
)
from opentelemetry.sdk.metrics.export.aggregate import (
    HistogramAggregator,
    SumAggregator,
    ValueObserverAggregator,
)
from opentelemetry.sdk.resources import Resource

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
class CloudMonitoringMetricsExporter(MetricsExporter):
    """ Implementation of Metrics Exporter to Google Cloud Monitoring

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
        """ Cloud Monitoring allows writing up to 200 time series at once

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
        self, record: ExportRecord
    ) -> Optional[MetricDescriptor]:
        """ We can map Metric to MetricDescriptor using Metric.name or
        MetricDescriptor.type. We create the MetricDescriptor if it doesn't
        exist already and cache it. Note that recreating MetricDescriptors is
        a no-op if it already exists.

        :param record:
        :return:
        """
        instrument = record.instrument
        descriptor_type = "custom.googleapis.com/OpenTelemetry/{}".format(
            instrument.name
        )
        if descriptor_type in self._metric_descriptors:
            return self._metric_descriptors[descriptor_type]

        descriptor = {  # type: ignore[var-annotated] # TODO #56
            "name": None,
            "type": descriptor_type,
            "display_name": instrument.name,
            "description": instrument.description,
            "labels": [],
        }
        for key, value in record.labels:
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

        # SumAggregator is best represented as a cumulative, but it can't be
        # represented that way if it can decrement. So we need to make sure
        # that the instrument is not an UpDownCounter
        if isinstance(record.aggregator, SumAggregator) and not isinstance(
            record.instrument, UpDownCounter
        ):
            descriptor["metric_kind"] = MetricDescriptor.MetricKind.CUMULATIVE
        elif isinstance(record.aggregator, ValueObserverAggregator):
            descriptor["metric_kind"] = MetricDescriptor.MetricKind.GAUGE
        elif isinstance(record.aggregator, HistogramAggregator):
            descriptor["metric_kind"] = MetricDescriptor.MetricKind.CUMULATIVE
        else:
            logger.warning(
                "Unsupported instrument/aggregator combo, types %s and %s, ignoring it",
                type(record.instrument).__name__,
                type(record.aggregator).__name__,
            )
            return None

        if isinstance(record.aggregator, HistogramAggregator):
            descriptor["value_type"] = MetricDescriptor.ValueType.DISTRIBUTION
        elif instrument.value_type == int:
            descriptor["value_type"] = MetricDescriptor.ValueType.INT64
        elif instrument.value_type == float:
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
            return None
        self._metric_descriptors[descriptor_type] = descriptor
        return descriptor

    def _set_start_end_times(self, point_dict, record, metric_descriptor):
        updated_key = (metric_descriptor.type, record.labels)
        seconds, nanos = divmod(
            record.aggregator.last_update_timestamp, NANOS_PER_SECOND
        )

        if (
            metric_descriptor.metric_kind
            == MetricDescriptor.MetricKind.CUMULATIVE
        ):
            if (
                record.instrument.meter.processor.stateful
                or updated_key not in self._last_updated
            ):
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
        ] = record.aggregator.last_update_timestamp

        point_dict["interval"]["end_time"] = {
            "seconds": seconds,
            "nanos": nanos,
        }

    def export(
        self, export_records: Sequence[ExportRecord]
    ) -> "MetricsExportResult":
        all_series = []
        for record in export_records:
            instrument = record.instrument
            metric_descriptor = self._get_metric_descriptor(record)
            if not metric_descriptor:
                continue
            series = TimeSeries(
                resource=self._get_monitored_resource(record.resource),
                # TODO: remove
                # https://github.com/GoogleCloudPlatform/opentelemetry-operations-python/issues/84
                metric_kind=metric_descriptor.metric_kind,
            )
            series.metric.type = metric_descriptor.type
            for key, value in record.labels:
                series.metric.labels[key] = str(value)

            if self.unique_identifier:
                series.metric.labels[
                    UNIQUE_IDENTIFIER_KEY
                ] = self.unique_identifier

            point_dict = {"interval": {}}  # type: ignore[var-annotated] # TODO #56

            if isinstance(record.aggregator, HistogramAggregator):
                bucket_bounds = list(record.aggregator.checkpoint.keys())
                bucket_values = list(record.aggregator.checkpoint.values())

                point_dict["value"] = {
                    "distribution_value": Distribution(
                        count=sum(bucket_values),
                        bucket_counts=bucket_values,
                        bucket_options={
                            "explicit_buckets": {
                                # don't put in > bucket
                                "bounds": bucket_bounds[:-1]
                            }
                        },
                    )
                }
            else:
                if isinstance(record.aggregator, SumAggregator):
                    data_point = record.aggregator.checkpoint
                elif isinstance(record.aggregator, ValueObserverAggregator):
                    data_point = record.aggregator.checkpoint.last

                if instrument.value_type == int:
                    point_dict["value"] = {"int64_value": data_point}
                elif instrument.value_type == float:
                    point_dict["value"] = {"double_value": data_point}

            seconds = (
                record.aggregator.last_update_timestamp // NANOS_PER_SECOND
            )

            # Cloud Monitoring API allows, for any combination of labels and
            # metric name, one update per WRITE_INTERVAL seconds
            updated_key = (metric_descriptor.type, record.labels)
            last_updated_time = self._last_updated.get(updated_key, 0)
            last_updated_time_seconds = last_updated_time // NANOS_PER_SECOND
            if seconds <= last_updated_time_seconds + WRITE_INTERVAL:
                continue

            self._set_start_end_times(point_dict, record, metric_descriptor)
            series.points.add(**point_dict)
            all_series.append(series)
        try:
            self._batch_write(all_series)
        # pylint: disable=broad-except
        except Exception as ex:
            logger.error(
                "Error while writing to Cloud Monitoring", exc_info=ex
            )
            return MetricsExportResult.FAILURE
        return MetricsExportResult.SUCCESS
