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
from io import StringIO
from textwrap import dedent
from typing import Mapping, Union

import pytest
from fixtures.cloud_logging_fake import (
    CloudLoggingFake,
    ExportAndAssertSnapshot,
)
from google.auth.credentials import AnonymousCredentials
from google.cloud.logging_v2.services.logging_service_v2 import (
    LoggingServiceV2Client,
)
from opentelemetry._logs.severity import SeverityNumber
from opentelemetry.exporter.cloud_logging import (
    CloudLoggingExporter,
    is_log_id_valid,
)
from opentelemetry.sdk._logs import LogData
from opentelemetry.sdk._logs._internal import LogRecord
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util.instrumentation import InstrumentationScope

PROJECT_ID = "fakeproject"

GEN_AI_DICT = {
    "gen_ai.input.messages": (
        {
            "role": "user",
            "parts": (
                {
                    "type": "text",
                    "content": "Get weather details in New Delhi and San Francisco?",
                },
            ),
        },
        {
            "role": "model",
            "parts": (
                {
                    "type": "tool_call",
                    "arguments": {"location": "New Delhi"},
                    "name": "get_current_weather",
                    "id": "get_current_weather_0",
                },
                {
                    "type": "tool_call",
                    "arguments": {"location": "San Francisco"},
                    "name": "get_current_weather",
                    "id": "get_current_weather_1",
                },
            ),
        },
        {
            "role": "user",
            "parts": (
                {
                    "type": "tool_call_response",
                    "response": {
                        "content": '{"temperature": 35, "unit": "C"}'
                    },
                    "id": "get_current_weather_0",
                },
                {
                    "type": "tool_call_response",
                    "response": {
                        "content": '{"temperature": 25, "unit": "C"}'
                    },
                    "id": "get_current_weather_1",
                },
            ),
        },
    ),
    "gen_ai.system_instructions": (
        {
            "type": "text",
            "content": "You are a clever language model",
        },
    ),
    "gen_ai.output.messages": (
        {
            "role": "model",
            "parts": (
                {
                    "type": "text",
                    "content": "The current temperature in New Delhi is 35°C, and in San Francisco, it is 25°C.",
                },
            ),
            "finish_reason": "stop",
        },
    ),
}


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


def test_user_agent(cloudloggingfake: CloudLoggingFake) -> None:
    cloudloggingfake.exporter.export(
        [
            LogData(
                log_record=LogRecord(
                    body="abc",
                    resource=Resource({}),
                ),
                instrumentation_scope=InstrumentationScope("test"),
            )
        ]
    )
    for call in cloudloggingfake.get_calls():
        assert (
            re.match(
                r"^opentelemetry-python \S+; google-cloud-logging-exporter \S+ grpc-python/\S+",
                call.user_agent,
            )
            is not None
        )


def test_agent_engine_monitored_resources(
    export_and_assert_snapshot: ExportAndAssertSnapshot,
) -> None:
    log_data = [
        LogData(
            log_record=LogRecord(
                body="valid agent engine",
                timestamp=1736976310997977393,
                resource=Resource(
                    {
                        "cloud.resource_id": "//aiplatform.googleapis.com/projects/some-project123-321/locations/europe-west3/reasoningEngines/8477639270431981568"
                    }
                ),
            ),
            instrumentation_scope=InstrumentationScope("test"),
        ),
        LogData(
            log_record=LogRecord(
                body="invalid 1",
                timestamp=1736976310997977393,
                resource=Resource(
                    {
                        "cloud.resource_id": "//aiplatform.googleapis.com/locations/europe-west3/reasoningEngines/8477639270431981568"
                    }
                ),
            ),
            instrumentation_scope=InstrumentationScope("test"),
        ),
        LogData(
            log_record=LogRecord(
                body="invalid 2",
                timestamp=1736976310997977393,
                resource=Resource(
                    {
                        "cloud.resource_id": "//aiplatform.googleapis.com/projects/some-project123-321/locations/europe-west3/reasoningEngines//8477639270431981568"
                    }
                ),
            ),
            instrumentation_scope=InstrumentationScope("test"),
        ),
        LogData(
            log_record=LogRecord(
                body="invalid 3",
                timestamp=1736976310997977393,
                resource=Resource(
                    {
                        "cloud.resource_id": "aiplatform.googleapis.com/projects/some-project123-321/locations/europe-west3/reasoningEngines//8477639270431981568"
                    }
                ),
            ),
            instrumentation_scope=InstrumentationScope("test"),
        ),
    ]
    export_and_assert_snapshot(log_data)


def test_convert_otlp_dict_body(
    export_and_assert_snapshot: ExportAndAssertSnapshot,
) -> None:
    log_data = [
        LogData(
            log_record=LogRecord(
                event_name="random.genai.event",
                timestamp=1736976310997977393,
                severity_number=SeverityNumber(20),
                trace_id=25,
                span_id=22,
                attributes={
                    "gen_ai.system": True,
                    "test": 23,
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
    export_and_assert_snapshot(log_data)


def test_convert_otlp_various_different_types_in_attrs_and_bytes_body(
    export_and_assert_snapshot: ExportAndAssertSnapshot,
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
    export_and_assert_snapshot(log_data)


def test_convert_non_json_dict_bytes(
    export_and_assert_snapshot: ExportAndAssertSnapshot,
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
    export_and_assert_snapshot(log_data)


def test_convert_gen_ai_body(
    export_and_assert_snapshot: ExportAndAssertSnapshot,
) -> None:
    log_data = [
        LogData(
            log_record=LogRecord(
                event_name="gen_ai.client.inference.operation.details",
                timestamp=1736976310997977393,
                body=GEN_AI_DICT,
            ),
            instrumentation_scope=InstrumentationScope("test"),
        )
    ]
    export_and_assert_snapshot(log_data)


def test_is_log_id_valid():
    assert is_log_id_valid(";") is False
    assert is_log_id_valid("aB12//..--__") is True
    assert is_log_id_valid("a" * 512) is False
    assert is_log_id_valid("abc1212**") is False
    assert is_log_id_valid("gen_ai.client.inference.operation.details") is True


def test_pick_log_id() -> None:
    exporter = CloudLoggingExporter(
        client=LoggingServiceV2Client(credentials=AnonymousCredentials()),
        project_id=PROJECT_ID,
        default_log_name="test",
    )
    assert (
        exporter.pick_log_id("valid_log_name_attr", "event_name_str")
        == "valid_log_name_attr"
    )
    assert (
        exporter.pick_log_id("invalid_attr**2", "event_name_str")
        == "event_name_str"
    )
    assert exporter.pick_log_id(None, "event_name_str") == "event_name_str"
    assert exporter.pick_log_id(None, None) == exporter.default_log_name
    assert (
        exporter.pick_log_id(None, "invalid_event_name_id24$")
        == exporter.default_log_name
    )


@pytest.mark.parametrize(
    "body",
    [
        pytest.param("A text body", id="str"),
        pytest.param(True, id="bool"),
        pytest.param(None, id="None"),
        pytest.param(
            {"my_dict": [{"key": b"bytes"}]}, id="list_of_dicts_with_bytes"
        ),
        pytest.param(
            {"my_dict": [True, False, False, True]}, id="list_of_bools"
        ),
        pytest.param(
            {"my_dict": [True, "str", 1, 0.234]}, id="list_of_mixed_sequence"
        ),
    ],
)
def test_convert_various_types_of_bodies(
    export_and_assert_snapshot: ExportAndAssertSnapshot,
    body: Union[str, bool, None, Mapping],
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
    export_and_assert_snapshot(log_data)


def test_convert_various_types_of_attributes(
    export_and_assert_snapshot: ExportAndAssertSnapshot,
) -> None:
    log_data = [
        LogData(
            log_record=LogRecord(
                attributes={
                    "a": [{"key": b"bytes"}],
                    "b": [True, False, False, True],
                    "c": {"a_dict": "abcd", "akey": 1234},
                    "d": GEN_AI_DICT,
                },
                timestamp=1736976310997977393,
            ),
            instrumentation_scope=InstrumentationScope("test"),
        )
    ]
    export_and_assert_snapshot(log_data)


def test_structured_json_lines():
    buf = StringIO()
    exporter = CloudLoggingExporter(
        project_id=PROJECT_ID, structured_json_file=buf
    )
    exporter.export(
        [
            LogData(
                log_record=LogRecord(
                    event_name="foo",
                    timestamp=1736976310997977393,
                    severity_number=SeverityNumber(20),
                    trace_id=25,
                    span_id=22,
                    attributes={"key": f"{i}"},
                    body="hello",
                ),
                instrumentation_scope=InstrumentationScope("test"),
            )
            for i in range(5)
        ]
    )
    assert buf.getvalue() == dedent(
        """\
        {"logging.googleapis.com/labels":{"event.name":"foo","key":"0"},"logging.googleapis.com/spanId":"0000000000000016","logging.googleapis.com/trace":"projects/fakeproject/traces/00000000000000000000000000000019","logging.googleapis.com/trace_sampled":false,"message":"hello","severity":"ERROR","time":"2025-01-15T21:25:10.997977393Z"}
        {"logging.googleapis.com/labels":{"event.name":"foo","key":"1"},"logging.googleapis.com/spanId":"0000000000000016","logging.googleapis.com/trace":"projects/fakeproject/traces/00000000000000000000000000000019","logging.googleapis.com/trace_sampled":false,"message":"hello","severity":"ERROR","time":"2025-01-15T21:25:10.997977393Z"}
        {"logging.googleapis.com/labels":{"event.name":"foo","key":"2"},"logging.googleapis.com/spanId":"0000000000000016","logging.googleapis.com/trace":"projects/fakeproject/traces/00000000000000000000000000000019","logging.googleapis.com/trace_sampled":false,"message":"hello","severity":"ERROR","time":"2025-01-15T21:25:10.997977393Z"}
        {"logging.googleapis.com/labels":{"event.name":"foo","key":"3"},"logging.googleapis.com/spanId":"0000000000000016","logging.googleapis.com/trace":"projects/fakeproject/traces/00000000000000000000000000000019","logging.googleapis.com/trace_sampled":false,"message":"hello","severity":"ERROR","time":"2025-01-15T21:25:10.997977393Z"}
        {"logging.googleapis.com/labels":{"event.name":"foo","key":"4"},"logging.googleapis.com/spanId":"0000000000000016","logging.googleapis.com/trace":"projects/fakeproject/traces/00000000000000000000000000000019","logging.googleapis.com/trace_sampled":false,"message":"hello","severity":"ERROR","time":"2025-01-15T21:25:10.997977393Z"}
        """
    ), "Each `LogData` should be on its own line"
