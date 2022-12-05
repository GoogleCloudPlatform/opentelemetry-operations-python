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

from typing import Optional, cast

import google.protobuf.message
import proto
import pytest
from fixtures.gcmfake import GcmCalls
from google.protobuf import json_format
from syrupy.extensions.json import JSONSnapshotExtension
from syrupy.matchers import path_type
from syrupy.types import (
    PropertyFilter,
    PropertyMatcher,
    SerializableData,
    SerializedData,
)


# pylint: disable=too-many-ancestors
class GcmCallsSnapshotExtension(JSONSnapshotExtension):
    """syrupy extension to serialize GcmCalls.

    Serializes the protobufs for each method call into JSON for storing as a snapshot.
    """

    def serialize(
        self,
        data: SerializableData,
        *,
        exclude: Optional[PropertyFilter] = None,
        matcher: Optional[PropertyMatcher] = None,
    ) -> SerializedData:
        gcmcalls = cast(GcmCalls, data)
        json = {}
        for method, calls in gcmcalls.items():
            dict_requests = []
            for call in calls:
                if isinstance(call.message, proto.message.Message):
                    call.message = type(call.message).pb(call.message)
                elif isinstance(call.message, google.protobuf.message.Message):
                    pass
                else:
                    raise ValueError(
                        f"Excepted a proto-plus or protobuf message, got {type(call)}"
                    )
                dict_requests.append(json_format.MessageToDict(call.message))
            json[method] = dict_requests

        return super().serialize(json, exclude=exclude, matcher=matcher)


@pytest.fixture(name="snapshot_gcmcalls")
def fixture_snapshot_gcmcalls(snapshot):
    """Fixture for snapshot testing of GcmCalls

    TimeInterval.start_time and TimeInterval.end_time timestamps are "redacted" since they are
    dynamic depending on when the test is run.
    """
    return snapshot.use_extension(GcmCallsSnapshotExtension)(
        matcher=path_type(
            {r".*\.interval\.(start|end)Time": (str,)},
            regex=True,
        )
    )
