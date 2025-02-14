# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from __future__ import annotations

import base64
import datetime
import json
import logging
import urllib.parse
from typing import Any, Mapping, Optional, Sequence

import google.auth
from google.api.monitored_resource_pb2 import (  # pylint: disable = no-name-in-module
    MonitoredResource,
)
from google.cloud.logging_v2.services.logging_service_v2 import (
    LoggingServiceV2Client,
)
from google.cloud.logging_v2.services.logging_service_v2.transports.grpc import (
    LoggingServiceV2GrpcTransport,
)
from google.cloud.logging_v2.types.log_entry import LogEntry
from google.cloud.logging_v2.types.logging import WriteLogEntriesRequest
from google.logging.type.log_severity_pb2 import (  # pylint: disable = no-name-in-module
    LogSeverity,
)
from google.protobuf.struct_pb2 import (  # pylint: disable = no-name-in-module
    Struct,
)
from google.protobuf.timestamp_pb2 import (  # pylint: disable = no-name-in-module
    Timestamp,
)
from opentelemetry.exporter.cloud_logging.version import __version__
from opentelemetry.resourcedetector.gcp_resource_detector._mapping import (
    get_monitored_resource,
)
from opentelemetry.sdk import version as opentelemetry_sdk_version
from opentelemetry.sdk._logs import LogData
from opentelemetry.sdk._logs.export import LogExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.trace import format_span_id, format_trace_id

DEFAULT_MAX_ENTRY_SIZE = 256000  # 256 KB
DEFAULT_MAX_REQUEST_SIZE = 10000000  # 10 MB

HTTP_REQUEST_ATTRIBUTE_KEY = "gcp.http_request"
LOG_NAME_ATTRIBUTE_KEY = "gcp.log_name"
SOURCE_LOCATION_ATTRIBUTE_KEY = "gcp.source_location"
TRACE_SAMPLED_ATTRIBUTE_KEY = "gcp.trace_sampled"
PROJECT_ID_ATTRIBUTE_KEY = "gcp.project_id"
_OTEL_SDK_VERSION = opentelemetry_sdk_version.__version__
_USER_AGENT = f"opentelemetry-python {_OTEL_SDK_VERSION}; google-cloud-logging-exporter {__version__}"

# Set user-agent metadata, see https://github.com/grpc/grpc/issues/23644 and default options
# from
# https://github.com/googleapis/python-logging/blob/5309478c054d0f2b9301817fd835f2098f51dc3a/google/cloud/logging_v2/services/logging_service_v2/transports/grpc.py#L179-L182
_OPTIONS = [
    ("grpc.max_send_message_length", -1),
    ("grpc.max_receive_message_length", -1),
    ("grpc.primary_user_agent", _USER_AGENT),
]

# severityMapping maps the integer severity level values from OTel [0-24]
# to matching Cloud Logging severity levels.
SEVERITY_MAPPING: dict[int, int] = {
    0: LogSeverity.DEFAULT,
    1: LogSeverity.DEBUG,
    2: LogSeverity.DEBUG,
    3: LogSeverity.DEBUG,
    4: LogSeverity.DEBUG,
    5: LogSeverity.DEBUG,
    6: LogSeverity.DEBUG,
    7: LogSeverity.DEBUG,
    8: LogSeverity.DEBUG,
    9: LogSeverity.INFO,
    10: LogSeverity.INFO,
    11: LogSeverity.NOTICE,
    12: LogSeverity.NOTICE,
    13: LogSeverity.WARNING,
    14: LogSeverity.WARNING,
    15: LogSeverity.WARNING,
    16: LogSeverity.WARNING,
    17: LogSeverity.ERROR,
    18: LogSeverity.ERROR,
    19: LogSeverity.ERROR,
    20: LogSeverity.ERROR,
    21: LogSeverity.CRITICAL,
    22: LogSeverity.CRITICAL,
    23: LogSeverity.ALERT,
    24: LogSeverity.EMERGENCY,
}


def _convert_any_value_to_string(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, bytes):
        return base64.b64encode(value).decode()
    if isinstance(value, (int, float, str)):
        return str(value)
    if isinstance(value, (list, tuple)):
        return json.dumps(value)
    logging.warning(
        "Unknown value %s found, cannot convert to string.", type(value)
    )
    return ""


def _set_payload_in_log_entry(log_entry: LogEntry, body: Any | None):
    struct = Struct()
    if isinstance(body, Mapping):
        struct.update(body)
        log_entry.json_payload = struct
    elif isinstance(body, bytes):
        json_str = body.decode("utf-8", errors="replace")
        json_dict = json.loads(json_str)
        if isinstance(json_dict, Mapping):
            struct.update(json_dict)
            log_entry.json_payload = struct
        else:
            log_entry.text_payload = base64.b64encode(body).decode()
    else:
        log_entry.text_payload = _convert_any_value_to_string(body)


class CloudLoggingExporter(LogExporter):
    def __init__(
        self,
        project_id: Optional[str] = None,
        default_log_name: Optional[str] = None,
        client: Optional[LoggingServiceV2Client] = None,
    ):
        self.project_id: str
        if not project_id:
            _, default_project_id = google.auth.default()
            self.project_id = str(default_project_id)
        else:
            self.project_id = project_id
        if default_log_name:
            self.default_log_name = default_log_name
        else:
            self.default_log_name = "otel_python_inprocess_log_name_temp"
        self.client = client or LoggingServiceV2Client(
            transport=LoggingServiceV2GrpcTransport(
                channel=LoggingServiceV2GrpcTransport.create_channel(
                    options=_OPTIONS,
                )
            )
        )

    def export(self, batch: Sequence[LogData]):
        now = datetime.datetime.now()
        log_entries = []
        for log_data in batch:
            log_entry = LogEntry()
            log_record = log_data.log_record
            attributes = log_record.attributes or {}
            project_id = str(
                attributes.get(PROJECT_ID_ATTRIBUTE_KEY, self.project_id)
            )
            log_suffix = urllib.parse.quote_plus(
                str(
                    attributes.get(
                        LOG_NAME_ATTRIBUTE_KEY, self.default_log_name
                    )
                )
            )
            log_entry.log_name = f"projects/{project_id}/logs/{log_suffix}"
            # If timestamp is unset fall back to observed_time_unix_nano as recommended,
            # see https://github.com/open-telemetry/opentelemetry-proto/blob/4abbb78/opentelemetry/proto/logs/v1/logs.proto#L176-L179
            ts = Timestamp()
            if log_record.timestamp or log_record.observed_timestamp:
                ts.FromNanoseconds(
                    log_record.timestamp or log_record.observed_timestamp
                )
            else:
                ts.FromDatetime(now)
            log_entry.timestamp = ts
            monitored_resource_data = get_monitored_resource(
                log_record.resource or Resource({})
            )
            if monitored_resource_data:
                log_entry.resource = MonitoredResource(
                    type=monitored_resource_data.type,
                    labels=monitored_resource_data.labels,
                )
            log_entry.trace_sampled = (
                log_record.trace_flags is not None
                and log_record.trace_flags.sampled
            )
            if log_record.trace_id:
                log_entry.trace = f"projects/{project_id}/traces/{format_trace_id(log_record.trace_id)}"
            if log_record.span_id:
                log_entry.span_id = format_span_id(log_record.span_id)
            if (
                log_record.severity_number
                and log_record.severity_number.value in SEVERITY_MAPPING
            ):
                log_entry.severity = SEVERITY_MAPPING[  # type: ignore[assignment]
                    log_record.severity_number.value  # type: ignore[index]
                ]
            log_entry.labels = {
                k: _convert_any_value_to_string(v)
                for k, v in attributes.items()
            }
            _set_payload_in_log_entry(log_entry, log_record.body)
            log_entries.append(log_entry)

        self._write_log_entries(log_entries)

    def _write_log_entries(self, log_entries: list[LogEntry]):
        batch: list[LogEntry] = []
        batch_byte_size = 0
        for entry in log_entries:
            msg_size = LogEntry.pb(entry).ByteSize()
            if msg_size > DEFAULT_MAX_ENTRY_SIZE:
                logging.warning(
                    "Cannot write log that is %s bytes which exceeds Cloud Logging's maximum limit of %s bytes.",
                    msg_size,
                    DEFAULT_MAX_ENTRY_SIZE,
                )
                continue
            if msg_size + batch_byte_size > DEFAULT_MAX_REQUEST_SIZE:
                try:
                    self.client.write_log_entries(
                        WriteLogEntriesRequest(
                            entries=batch, partial_success=True
                        )
                    )
                # pylint: disable=broad-except
                except Exception as ex:
                    logging.error(
                        "Error while writing to Cloud Logging", exc_info=ex
                    )
                batch = [entry]
                batch_byte_size = msg_size
            else:
                batch.append(entry)
                batch_byte_size += msg_size
        if batch:
            try:
                self.client.write_log_entries(
                    WriteLogEntriesRequest(entries=batch, partial_success=True)
                )
            # pylint: disable=broad-except
            except Exception as ex:
                logging.error(
                    "Error while writing to Cloud Logging", exc_info=ex
                )

    def shutdown(self):
        pass
