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

from __future__ import annotations

from typing import Any

from google.cloud.aiplatform_v1.types import (
    GenerateContentRequest as v1GenerateContentRequest,
)
from google.cloud.aiplatform_v1beta1.types import (
    GenerateContentRequest,
)
from langchain_core.messages import (
    BaseMessage,
)
from langchain_google_vertexai import ChatVertexAI


class PatchedChatVertexAI(ChatVertexAI):
    def _prepare_request_gemini(
        self, messages: list[BaseMessage], *args: Any, **kwargs: Any
    ) -> v1GenerateContentRequest | GenerateContentRequest:
        # See https://github.com/langchain-ai/langchain-google/issues/886
        #
        # Filter out any blocked messages with no content which can appear if you have a blocked
        # message from finish_reason SAFETY:
        #
        # AIMessage(
        #     content="",
        #     additional_kwargs={},
        #     response_metadata={
        #         "is_blocked": True,
        #         "safety_ratings": [ ... ],
        #         "finish_reason": "SAFETY",
        #     },
        #     ...
        # )
        #
        # These cause `google.api_core.exceptions.InvalidArgument: 400 Unable to submit request
        # because it must include at least one parts field`

        messages = [
            message
            for message in messages
            if not message.response_metadata.get("is_blocked", False)
        ]
        return super()._prepare_request_gemini(messages, *args, **kwargs)
