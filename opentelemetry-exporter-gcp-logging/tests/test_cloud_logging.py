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
"""
Some tests in this file use [syrupy](https://github.com/tophat/syrupy) for snapshot testing aka
golden testing. The Cloud Logging API calls are captured with a gRPC fake and compared to the existing
snapshot file in the __snapshots__ directory.

If an expected behavior change is made to the exporter causing these tests to fail, regenerate
the snapshots by running tox to pass the --snapshot-update flag to pytest:

```sh
tox -e py310-ci-test-cloudlogging -- --snapshot-update
```

Be sure to review the changes.
"""
import re
from typing import List

from fixtures.cloud_logging_fake import CloudLoggingFake, WriteLogEntriesCall
from google.cloud.logging_v2.services.logging_service_v2 import (
    LoggingServiceV2Client,
)
from opentelemetry._logs.severity import SeverityNumber
from opentelemetry.exporter.cloud_logging import CloudLoggingExporter
from opentelemetry.sdk._logs import LogData
from opentelemetry.sdk._logs._internal import LogRecord
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope
from google.auth.credentials import AnonymousCredentials

PROJECT_ID = "fakeproject"


def test_create_cloud_logging_exporter() -> None:
    CloudLoggingExporter(default_log_name="test")
    client = LoggingServiceV2Client(credentials=AnonymousCredentials())
    CloudLoggingExporter(project_id=PROJECT_ID, client=client)


def test_invalid_otlp_entries_raise_warnings(caplog) -> None:
    client = LoggingServiceV2Client(credentials=AnonymousCredentials())
    no_default_logname = CloudLoggingExporter(
        project_id=PROJECT_ID, client=client
    )
    attrs = {str(i):"i" * 10000 for i in range(1000)}
    log_record = LogRecord(resource=Resource({}),
                            attributes=attrs)
    no_default_logname.export(
        [
            LogData(
                log_record=log_record,
                instrumentation_scope=InstrumentationScope("test"),
            )
        ]
    )
    assert len(caplog.records) == 1
    assert "exceeds Cloud Logging's maximum limit of 256000.\n" in caplog.text


def test_convert_otlp(
    cloudloggingfake: CloudLoggingFake,
    snapshot_writelogentrycalls: List[WriteLogEntriesCall],
) -> None:
    # Create a new LogRecord object
    log_record = LogRecord(
        timestamp=1736976310997977393,
        severity_number=SeverityNumber(20),
        trace_id=25,
        span_id=22,
        attributes={
            "gen_ai.system": "openai",
            "event.name": "gen_ai.system.message",
        },
        body={
            "kvlistValue": {
                "values": [
                    {
                        "key": "content",
                        "value": {
                            "stringValue": "You're a helpful assistant."
                        },
                    }
                ]
            }
        },
        # Not sure why I'm getting  AttributeError: 'NoneType' object has no attribute 'attributes' when unset.
        resource=Resource({}),
    )

    log_data = [
        LogData(
            log_record=log_record,
            instrumentation_scope=InstrumentationScope("test"),
        )
    ]
    cloudloggingfake.exporter.export(log_data)
    assert cloudloggingfake.get_calls() == snapshot_writelogentrycalls
    for call in cloudloggingfake.get_calls():
        assert (
            re.match(
                r"^opentelemetry-python \S+; google-cloud-logging-exporter \S+ grpc-python/\S+",
                call.user_agent,
            )
            is not None
        )
