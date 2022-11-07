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
from typing import Callable, Iterable, List, Mapping, Tuple

import grpc
import pytest
from google.api.metric_pb2 import MetricDescriptor
from google.cloud.monitoring_v3 import (
    CreateMetricDescriptorRequest,
    CreateTimeSeriesRequest,
    MetricServiceClient,
)
from google.cloud.monitoring_v3.services.metric_service.transports import (
    MetricServiceGrpcTransport,
)

# pylint: disable=no-name-in-module
from google.protobuf.empty_pb2 import Empty
from google.protobuf.message import Message
from grpc import (
    GenericRpcHandler,
    RpcContext,
    RpcMethodHandler,
    insecure_channel,
    method_handlers_generic_handler,
    unary_unary_rpc_method_handler,
)

# Mapping of fully qualified GCM API method names to list of requests received
GcmCalls = Mapping[str, List[Message]]


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
        behavior: Callable[[Message, RpcContext], Message],
        deserializer,
        serializer,
    ) -> Tuple[str, RpcMethodHandler]:
        def impl(req: Message, context: RpcContext) -> Message:
            self._calls[f"/{self._service}/{method}"].append(req)
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
    client: MetricServiceClient
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
            with insecure_channel(f"localhost:{port}") as channel:
                yield GcmFake(
                    client=MetricServiceClient(
                        transport=MetricServiceGrpcTransport(channel=channel),
                    ),
                    get_calls=handler.get_calls,
                )
    finally:
        if server:
            server.stop(None)
