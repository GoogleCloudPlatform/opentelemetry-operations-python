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


from typing import TYPE_CHECKING, List, Optional, cast

from google.protobuf import json_format
from syrupy.extensions.json import JSONSnapshotExtension
from syrupy.types import (
    PropertyFilter,
    PropertyMatcher,
    SerializableData,
    SerializedData,
)

if TYPE_CHECKING:
    from fixtures.cloud_logging_fake import WriteLogEntriesCall


# pylint: disable=too-many-ancestors
class WriteLogEntryCallSnapshotExtension(JSONSnapshotExtension):
    """syrupy extension to serialize WriteLogEntriesRequest to JSON for storing as a snapshot."""

    def serialize(
        self,
        data: SerializableData,
        *,
        exclude: Optional[PropertyFilter] = None,
        matcher: Optional[PropertyMatcher] = None,
    ) -> SerializedData:
        json = [
            json_format.MessageToDict(
                type(call.write_log_entries_request).pb(
                    call.write_log_entries_request
                )
            )
            for call in cast(List["WriteLogEntriesCall"], data)
        ]
        return super().serialize(json, exclude=exclude, matcher=matcher)
