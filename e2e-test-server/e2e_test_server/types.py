# Copyright 2021 Google LLC
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

import base64
from dataclasses import dataclass
from typing import Mapping, Protocol

from pydantic import BaseModel, Field


@dataclass(frozen=True)
class PubsubMessage:
    """Wrapper for message that can be used for push and pull apis"""

    attributes: Mapping[str, str]
    data: bytes


class PubsubPushPayload(BaseModel):
    """Shape of the JSON payload coming from a push subscription"""

    class Message(BaseModel):
        attributes: Mapping[str, str]
        data_base64: str = Field(default="", alias="data")

        def to_pubsub_message(self) -> PubsubMessage:
            return PubsubMessage(
                attributes=self.attributes,
                data=base64.b64decode(self.data_base64),
            )

    message: Message
    subscription: str
