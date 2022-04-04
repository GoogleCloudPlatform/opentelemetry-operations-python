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

from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter

# private import for testing only
from opentelemetry.sdk._configuration import _import_exporters


class TestCloudTraceAutoInstrument(TestCase):
    def test_loads_cloud_trace_exporter(self):
        """Test that OTel configuration internals can load the trace exporter from entrypoint
        by name"""
        trace_exporters, _ = _import_exporters(
            trace_exporter_names=["gcp_trace"], log_exporter_names=[]
        )
        self.assertEqual(
            trace_exporters, {"gcp_trace": CloudTraceSpanExporter}
        )
