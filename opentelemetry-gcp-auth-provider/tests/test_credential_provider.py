# Copyright 2023 Google LLC
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
from os import environ
from unittest import TestCase
from unittest.mock import patch

from google.auth.transport.requests import AuthorizedSession
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter as GRPCOTLPSpanExporter,
)
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter,
)

# private import for testing only
from opentelemetry.sdk._configuration import _init_exporter
from opentelemetry.sdk.environment_variables import (
    OTEL_PYTHON_EXPORTER_OTLP_TRACES_CREDENTIAL_PROVIDER,
)


# These tests will not pass until the upstream PR is submitted.
class TestOTLPTraceAutoInstrumentGcpCredential(TestCase):
    @patch.dict(
        environ,
        {
            OTEL_PYTHON_EXPORTER_OTLP_TRACES_CREDENTIAL_PROVIDER: "gcp_http_authorized_session"
        },
    )
    def test_loads_otlp_http_exporter_with_google_session(self):
        """Test that OTel configuration internals can load the credentials from entrypoint by
        name"""

        exporter = _init_exporter(
            "traces",
            {},
            OTLPSpanExporter,
            otlp_credential_param_for_all_signal_types=None,
        )
        assert isinstance(exporter._session, AuthorizedSession)

    @patch.dict(
        environ,
        {
            OTEL_PYTHON_EXPORTER_OTLP_TRACES_CREDENTIAL_PROVIDER: "gcp_grpc_channel_credentials"
        },
    )
    def test_loads_otlp_grpc_exporter_with_google_channel_creds(self):
        """Test that OTel configuration internals can load the credentials from entrypoint by
        name"""

        exporter = _init_exporter(
            "traces",
            {},
            GRPCOTLPSpanExporter,
            otlp_credential_param_for_all_signal_types=None,
        )
        # TODO: Figure out how to assert something about exporter.credentials. google's grpc credentials obj look exactly like
        # the default one..
