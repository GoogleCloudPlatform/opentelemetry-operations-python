# Copyright 2021 Google
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

import os
import enum


class SubscriptionMode(enum.Enum):
    PULL = "pull"
    PUSH = "push"


INSTRUMENTING_MODULE_NAME = "opentelemetry-ops-e2e-test-server"
SCENARIO = "scenario"
STATUS_CODE = "status_code"
TEST_ID = "test_id"
SUBSCRIPTION_MODE: SubscriptionMode = SubscriptionMode(
    os.environ["SUBSCRIPTION_MODE"]
)
PROJECT_ID = os.environ["PROJECT_ID"]
REQUEST_SUBSCRIPTION_NAME = os.environ["REQUEST_SUBSCRIPTION_NAME"]
RESPONSE_TOPIC_NAME = os.environ["RESPONSE_TOPIC_NAME"]
