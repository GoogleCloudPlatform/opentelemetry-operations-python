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
from typing import List, Union

import pytest
from fixtures.cloud_logging_fake import CloudLoggingFake, WriteLogEntriesCall
from google.auth.credentials import AnonymousCredentials
from google.cloud.logging_v2.services.logging_service_v2 import (
    LoggingServiceV2Client,
)
from opentelemetry._logs.severity import SeverityNumber
from opentelemetry.exporter.cloud_logging import CloudLoggingExporter
from opentelemetry.sdk._logs import LogData
from opentelemetry.sdk._logs._internal import LogRecord
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope

PROJECT_ID = "fakeproject"


def test_too_large_log_raises_warning(caplog) -> None:
    client = LoggingServiceV2Client(credentials=AnonymousCredentials())
    no_default_logname = CloudLoggingExporter(
        project_id=PROJECT_ID, client=client
    )
    no_default_logname.export(
        [
            LogData(
                log_record=LogRecord(
                    body="abc",
                    resource=Resource({}),
                    attributes={str(i): "i" * 10000 for i in range(1000)},
                ),
                instrumentation_scope=InstrumentationScope("test"),
            )
        ]
    )
    assert len(caplog.records) == 1
    assert (
        "exceeds Cloud Logging's maximum limit of 256000 bytes" in caplog.text
    )


def test_convert_otlp_dict_body(
    cloudloggingfake: CloudLoggingFake,
    snapshot_writelogentrycalls: List[WriteLogEntriesCall],
) -> None:
    log_data = [
        LogData(
            log_record=LogRecord(
                timestamp=1736976310997977393,
                severity_number=SeverityNumber(20),
                trace_id=25,
                span_id=22,
                attributes={
                    "gen_ai.system": True,
                    "test": 23,
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
                        ],
                        "bytes_field": b"bytes",
                        "repeated_bytes_field": [b"bytes", b"bytes", b"bytes"],
                    }
                },
            ),
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


def test_convert_otlp_various_different_types_in_attrs_and_bytes_body(
    cloudloggingfake: CloudLoggingFake,
    snapshot_writelogentrycalls: List[WriteLogEntriesCall],
) -> None:
    log_data = [
        LogData(
            log_record=LogRecord(
                timestamp=1736976310997977393,
                attributes={
                    "int": 25,
                    "float": 25.43231,
                    "intArray": [21, 18, 23, 17],
                    "boolArray": [True, False, True, True],
                },
                body=b'{"Date": "2016-05-21T21:35:40Z", "CreationDate": "2012-05-05", "LogoType": "png", "Ref": 164611595, "Classe": ["Email addresses", "Passwords"],"Link":"http://some_link.com"}',
            ),
            instrumentation_scope=InstrumentationScope("test"),
        )
    ]
    cloudloggingfake.exporter.export(log_data)
    assert cloudloggingfake.get_calls() == snapshot_writelogentrycalls


def test_convert_non_json_dict_bytes(
    cloudloggingfake: CloudLoggingFake,
    snapshot_writelogentrycalls: List[WriteLogEntriesCall],
) -> None:
    log_data = [
        LogData(
            log_record=LogRecord(
                timestamp=1736976310997977393,
                body=b"123",
            ),
            instrumentation_scope=InstrumentationScope("test"),
        )
    ]
    cloudloggingfake.exporter.export(log_data)
    assert cloudloggingfake.get_calls() == snapshot_writelogentrycalls


@pytest.mark.parametrize(
    "body",
    [
        pytest.param("A text body", id="str"),
        pytest.param(True, id="bool"),
        pytest.param(None, id="None"),
    ],
)
def test_convert_various_types_of_bodies(
    cloudloggingfake: CloudLoggingFake,
    snapshot_writelogentrycalls: List[WriteLogEntriesCall],
    body: Union[str, bool, None],
) -> None:
    log_data = [
        LogData(
            log_record=LogRecord(
                timestamp=1736976310997977393,
                body=body,
            ),
            instrumentation_scope=InstrumentationScope("test"),
        )
    ]
    cloudloggingfake.exporter.export(log_data)
    assert cloudloggingfake.get_calls() == snapshot_writelogentrycalls
