# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import partial
from typing import Callable, Iterable, List, Mapping, Tuple, Type, cast
from unittest.mock import patch

import grpc
import pytest
from google.api.metric_pb2 import (  # pylint: disable=no-name-in-module
    MetricDescriptor,
)
from google.cloud.monitoring_v3 import (
    CreateMetricDescriptorRequest,
    CreateTimeSeriesRequest,
)
from google.cloud.monitoring_v3.services.metric_service.transports import (
    MetricServiceGrpcTransport,
)

# pylint: disable=no-name-in-module
from google.protobuf.empty_pb2 import Empty
from google.protobuf.message import Message
from grpc import (
    GenericRpcHandler,
    RpcMethodHandler,
    ServicerContext,
    insecure_channel,
    method_handlers_generic_handler,
    unary_unary_rpc_method_handler,
)
from opentelemetry.exporter.cloud_monitoring import (
    CloudMonitoringMetricsExporter,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader


@dataclass
class GcmCall:
    message: Message
    user_agent: str


GcmCalls = Mapping[str, List[GcmCall]]

PROJECT_ID = "fakeproject"


class FakeHandler(GenericRpcHandler):
    """gRPC handler partially implementing the GCM API and capturing the requests.

    Captures the request protos made to each method.
    """

    _service = "google.monitoring.v3.MetricService"

    def __init__(self):
        # pylint: disable=no-member
        super().__init__()
        self._calls: GcmCalls = defaultdict(list)

        self._wrapped = method_handlers_generic_handler(
            self._service,
            dict(
                [
                    self._make_impl(
                        "CreateTimeSeries",
                        lambda req, ctx: Empty(),
                        CreateTimeSeriesRequest.deserialize,
                        Empty.SerializeToString,
                    ),
                    self._make_impl(
                        "CreateMetricDescriptor",
                        # return the metric descriptor back
                        lambda req, ctx: req.metric_descriptor,
                        CreateMetricDescriptorRequest.deserialize,
                        MetricDescriptor.SerializeToString,
                    ),
                ]
            ),
        )

    def _make_impl(
        self,
        method: str,
        behavior: Callable[[Message, ServicerContext], Message],
        deserializer,
        serializer,
    ) -> Tuple[str, RpcMethodHandler]:
        def impl(req: Message, context: ServicerContext) -> Message:
            metadata_dict = dict(context.invocation_metadata())
            user_agent = cast(str, metadata_dict["user-agent"])
            self._calls[f"/{self._service}/{method}"].append(
                GcmCall(message=req, user_agent=user_agent)
            )
            return behavior(req, context)

        return method, unary_unary_rpc_method_handler(
            impl,
            request_deserializer=deserializer,
            response_serializer=serializer,
        )

    def service(self, handler_call_details):
        res = self._wrapped.service(handler_call_details)
        return res

    def get_calls(self) -> GcmCalls:
        """Returns calls made to each GCM API method"""
        return self._calls


@dataclass
class GcmFake:
    exporter: CloudMonitoringMetricsExporter
    get_calls: Callable[[], GcmCalls]


@pytest.fixture(name="gcmfake")
def fixture_gcmfake() -> Iterable[GcmFake]:
    """Fixture providing faked GCM api with captured requests"""

    handler = FakeHandler()
    server = None

    try:
        # Run in a single thread to serialize requests
        with ThreadPoolExecutor(1) as executor:
            server = grpc.server(executor, handlers=[handler])
            port = server.add_insecure_port("localhost:0")
            server.start()

            # patch MetricServiceGrpcTransport.create_channel staticmethod to return an insecure
            # channel but otherwise respect any parameters passed to it
            with patch.object(
                MetricServiceGrpcTransport,
                "create_channel",
                partial(insecure_channel, target=f"localhost:{port}"),
            ):
                yield GcmFake(
                    exporter=CloudMonitoringMetricsExporter(
                        project_id=PROJECT_ID
                    ),
                    get_calls=handler.get_calls,
                )
    finally:
        if server:
            server.stop(None)


GcmFakeMeterProvider = Type[MeterProvider]


@pytest.fixture(name="gcmfake_meter_provider")
def fixture_make_meter_provider(
    gcmfake: GcmFake,
) -> Iterable[GcmFakeMeterProvider]:
    """A factory fixture to create MeterProviders with GCM exporting pointing to the gcmfake

    Uses https://docs.pytest.org/en/7.1.x/how-to/fixtures.html#factories-as-fixtures pattern.
    Shuts down all created MeterProviders once the test is over.
    """
    mps: List[MeterProvider] = []

    def make_meter_provider(**kwargs) -> MeterProvider:
        mp = MeterProvider(
            **{
                "metric_readers": [
                    PeriodicExportingMetricReader(gcmfake.exporter)
                ],
                "shutdown_on_exit": False,
                **kwargs,
            }
        )
        mps.append(mp)
        return mp

    yield make_meter_provider
    for mp in mps:
        mp.shutdown()
