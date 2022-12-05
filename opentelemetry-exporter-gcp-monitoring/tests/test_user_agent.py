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

import re

from fixtures.gcmfake import GcmFake, GcmFakeMeterProvider


def test_with_resource(
    gcmfake_meter_provider: GcmFakeMeterProvider,
    gcmfake: GcmFake,
) -> None:
    meter_provider = gcmfake_meter_provider()
    counter = meter_provider.get_meter(__name__).create_counter(
        "mycounter", description="foo", unit="{myunit}"
    )
    counter.add(12)
    meter_provider.force_flush()

    for calls in gcmfake.get_calls().values():
        for call in calls:
            assert (
                re.match(
                    r"^opentelemetry-python \S+; google-cloud-metric-exporter \S+ grpc-python/\S+",
                    call.user_agent,
                )
                is not None
            )
