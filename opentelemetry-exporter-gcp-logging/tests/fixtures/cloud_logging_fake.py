# Copyright 2025 Google LLC
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
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import partial
from io import StringIO
from typing import Callable, Iterable, List, Sequence, cast
from unittest.mock import patch

import grpc
import pytest
from fixtures.snapshot_logging_calls import WriteLogEntryCallSnapshotExtension
from google.cloud.logging_v2.services.logging_service_v2.transports.grpc import (
    LoggingServiceV2GrpcTransport,
)
from google.cloud.logging_v2.types.logging import WriteLogEntriesRequest

# pylint: disable=no-name-in-module
from google.protobuf.empty_pb2 import Empty
from grpc import (
    GenericRpcHandler,
    ServicerContext,
    insecure_channel,
    method_handlers_generic_handler,
    unary_unary_rpc_method_handler,
)
from opentelemetry.exporter.cloud_logging import CloudLoggingExporter
from opentelemetry.sdk._logs import LogData
from syrupy.assertion import SnapshotAssertion
from syrupy.extensions.json import JSONSnapshotExtension


@dataclass
class WriteLogEntriesCall:
    write_log_entries_request: WriteLogEntriesRequest
    user_agent: str


PROJECT_ID = "fakeproject"


class FakeWriteLogEntriesHandler(GenericRpcHandler):
    """gRPC handler captures request protos made to Cloud Logging's WriteLogEntries."""

    _service = "google.logging.v2.LoggingServiceV2"
    _method = "WriteLogEntries"

    def __init__(self):
        # pylint: disable=no-member
        super().__init__()
        self._calls: List[WriteLogEntriesCall] = []

        def write_log_entries_request_handler(
            req: WriteLogEntriesRequest, context: ServicerContext
        ) -> Empty:
            metadata_dict = dict(context.invocation_metadata())
            self._calls.append(
                WriteLogEntriesCall(
                    write_log_entries_request=req,
                    user_agent=cast(str, metadata_dict["user-agent"]),
                )
            )
            return Empty()

        self._wrapped = method_handlers_generic_handler(
            self._service,
            {
                self._method: unary_unary_rpc_method_handler(
                    write_log_entries_request_handler,
                    WriteLogEntriesRequest.deserialize,
                    Empty.SerializeToString,
                )
            },
        )

    def service(self, handler_call_details):
        res = self._wrapped.service(handler_call_details)
        return res

    def get_calls(self) -> List[WriteLogEntriesCall]:
        """Returns calls made to WriteLogEntries"""
        return self._calls


@dataclass
class CloudLoggingFake:
    exporter: CloudLoggingExporter
    get_calls: Callable[[], List[WriteLogEntriesCall]]


@pytest.fixture(name="cloudloggingfake")
def fixture_cloudloggingfake() -> Iterable[CloudLoggingFake]:
    """Fixture providing faked Cloud Logging api with captured requests"""

    handler = FakeWriteLogEntriesHandler()
    server = None

    try:
        # Run in a single thread to serialize requests
        with ThreadPoolExecutor(1) as executor:
            server = grpc.server(executor, handlers=[handler])
            port = server.add_insecure_port("localhost:0")
            server.start()

            # patch LoggingServiceV2Transport.create_channel staticmethod to return an insecure
            # channel but otherwise respect any parameters passed to it
            with patch.object(
                LoggingServiceV2GrpcTransport,
                "create_channel",
                partial(insecure_channel, target=f"localhost:{port}"),
            ):
                yield CloudLoggingFake(
                    exporter=CloudLoggingExporter(
                        project_id=PROJECT_ID,
                        default_log_name="test",
                    ),
                    get_calls=handler.get_calls,
                )
    finally:
        if server:
            server.stop(None)


ExportAndAssertSnapshot = Callable[[Sequence[LogData]], None]


@pytest.fixture(
    name="export_and_assert_snapshot", params=["client", "structured_json"]
)
def fixture_export_and_assert_snapshot(
    request: pytest.FixtureRequest,
    snapshot: SnapshotAssertion,
) -> ExportAndAssertSnapshot:
    if request.param == "client":
        cloudloggingfake: CloudLoggingFake = request.getfixturevalue(
            "cloudloggingfake"
        )

        def export_and_assert_snapshot(log_data: Sequence[LogData]) -> None:
            cloudloggingfake.exporter.export(log_data)

            assert cloudloggingfake.get_calls() == snapshot(
                extension_class=WriteLogEntryCallSnapshotExtension
            )

        return export_and_assert_snapshot

    # pylint: disable=function-redefined
    def export_and_assert_snapshot(log_data: Sequence[LogData]) -> None:
        buf = StringIO()
        exporter = CloudLoggingExporter(
            project_id=PROJECT_ID, structured_json_file=buf
        )
        exporter.export(log_data)
        buf.seek(0)
        as_dict = [json.loads(line) for line in buf]
        assert as_dict == snapshot(extension_class=JSONSnapshotExtension)

    return export_and_assert_snapshot
