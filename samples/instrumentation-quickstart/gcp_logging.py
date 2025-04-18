# Copyright 2024 Google LLC
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

import logging

from opentelemetry.instrumentation.logging import LoggingInstrumentor
from pythonjsonlogger import jsonlogger


# [START opentelemetry_instrumentation_setup_logging]
def setup_structured_logging() -> None:
    LoggingInstrumentor().instrument()

    log_handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(message)s %(otelTraceID)s %(otelSpanID)s %(otelTraceSampled)s",
        rename_fields={
            "levelname": "severity",
            "asctime": "timestamp",
            "otelTraceID": "logging.googleapis.com/trace",
            "otelSpanID": "logging.googleapis.com/spanId",
            "otelTraceSampled": "logging.googleapis.com/trace_sampled",
        },
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )
    log_handler.setFormatter(formatter)
    logging.basicConfig(
        level=logging.INFO,
        handlers=[log_handler],
    )


# [END opentelemetry_instrumentation_setup_logging]
