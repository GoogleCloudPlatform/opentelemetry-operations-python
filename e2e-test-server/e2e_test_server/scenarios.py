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

import contextlib
import os
from dataclasses import dataclass
from typing import Any, Iterator, Mapping

from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ALWAYS_ON
from opentelemetry.trace import Tracer

from .constants import INSTRUMENTING_MODULE_NAME, TEST_ID


@dataclass
class Response:
    # HTTP style status code, even for pubsub
    status: int


@contextlib.contextmanager
def _tracer_setup(carrier: Mapping[str, str]) -> Iterator[tuple[str, Tracer]]:
    """\
    Context manager with common setup for tracing endpoints

    Yields a tracer (from a fresh SDK with new exporter) then finally flushes
    spans created during the test after.
    """

    tracer_provider = TracerProvider(
        sampler=ALWAYS_ON,
        active_span_processor=BatchSpanProcessor(
            CloudTraceSpanExporter(project_id=os.environ.get("PROJECT_ID"))
        ),
    )
    tracer = tracer_provider.get_tracer(INSTRUMENTING_MODULE_NAME)

    try:
        yield tracer
    finally:
        tracer_provider.shutdown()


def health(test_id: str, headers: Mapping[str, str], body: bytes) -> Response:
    return Response(status=200)


def basicTrace(
    test_id: str, headers: Mapping[str, str], body: bytes
) -> Response:
    """Create a basic trace"""

    with _tracer_setup(headers) as tracer:
        with tracer.start_span("basicTrace", attributes={TEST_ID: test_id}):
            pass

    return Response(status=200)
