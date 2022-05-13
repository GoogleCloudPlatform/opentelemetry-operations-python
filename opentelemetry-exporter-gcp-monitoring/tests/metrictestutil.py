# Copyright The OpenTelemetry Authors
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


from collections import OrderedDict

from opentelemetry.attributes import BoundedAttributes
from opentelemetry.sdk._metrics.point import (
    AggregationTemporality,
    Gauge,
    Histogram,
    Metric,
    Sum,
)
from opentelemetry.sdk.resources import Resource as SDKResource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope


def _generate_metric(
    name, point, attributes=None, description=None, unit=None, resource=None
) -> Metric:
    if attributes is None:
        attributes = BoundedAttributes(attributes={"a": 1, "b": True})
    if not description:
        description = "foo"
    if not unit:
        unit = "s"
    if not resource:
        resource =SDKResource(OrderedDict([("a", 1), ("b", False)]))
    return Metric(
        resource=resource,
        instrumentation_scope=InstrumentationScope(
            "first_name", "first_version"
        ),
        attributes=attributes,
        description=description,
        name=name,
        unit=unit,
        point=point,
    )


def _generate_sum(
    name, val, attributes=None, description=None, unit=None, resource=None
) -> Sum:
    return _generate_metric(
        name,
        Sum(
            aggregation_temporality=AggregationTemporality.CUMULATIVE,
            is_monotonic=True,
            start_time_unix_nano=1641946015139533244,
            time_unix_nano=1641946016139533244,
            value=val,
        ),
        attributes=attributes,
        description=description,
        unit=unit,
        resource=resource
    )


def _generate_gauge(
    name, val, attributes=None, description=None, unit=None
) -> Gauge:
    return _generate_metric(
        name,
        Gauge(
            time_unix_nano=1641946016139533244,
            value=val,
        ),
        attributes=attributes,
        description=description,
        unit=unit,
    )


def _generate_histogram(
    name, bucket_counts, explicit_bounds, max, min, sum, attributes=None, description=None, unit=None
) -> Histogram:
    return _generate_metric(
        name,
        Histogram(
            aggregation_temporality=AggregationTemporality.CUMULATIVE,
            bucket_counts=bucket_counts,
            explicit_bounds=explicit_bounds,
            max=max,
            min=min,
            start_time_unix_nano=1641946015139533244,
            sum=sum,
            time_unix_nano=1641946016139533244,
        ),
        attributes=attributes,
        description=description,
        unit=unit,
    )


def _generate_unsupported_metric(
    name, attributes=None, description=None, unit=None
) -> Sum:
    return _generate_metric(
        name,
        None,
        attributes=attributes,
        description=description,
        unit=unit,
    )
