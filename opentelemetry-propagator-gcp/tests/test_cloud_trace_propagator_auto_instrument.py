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

from unittest import TestCase
from unittest.mock import patch

from opentelemetry.environment_variables import OTEL_PROPAGATORS
from opentelemetry.propagators.cloud_trace_propagator import (
    CloudTraceFormatPropagator,
)


class TestCloudTracePropagatorAutoInstrument(TestCase):
    @patch.dict("os.environ", {OTEL_PROPAGATORS: "gcp_trace"})
    def test_loads_cloud_trace_propagator(self):
        # This test is a bit fragile as the propagator entry points are loaded on the first
        # import of opentelemetry.propagate and saved in a global variable. If another tests
        # imports that before this one, it can fail.
        # pylint: disable=import-outside-toplevel
        from opentelemetry.propagate import propagators

        self.assertEqual(len(propagators), 1)
        self.assertIsInstance(propagators[0], CloudTraceFormatPropagator)
