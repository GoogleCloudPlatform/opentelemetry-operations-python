# Copyright 2021 The OpenTelemetry Authors
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

"""Cloud Trace Span Propagator for X-Cloud-Trace-Context format.

Usage
-----

.. code-block:: python

    from opentelemetry.propagate import set_global_textmap
    from opentelemetry.propagators.cloud_trace_propagator import (
        CloudTraceFormatPropagator,
    )

    # Set the X-Cloud-Trace-Context header
    set_global_textmap(CloudTraceFormatPropagator())

Auto-instrumentation
--------------------

This exporter can also be used with the :envvar:`OTEL_PROPAGATORS` environment variable as
``OTEL_PROPAGATORS=gcp_trace``.

This also works with `OpenTelemetry auto-instrumentation
<https://opentelemetry.io/docs/instrumentation/python/automatic/>`_:

.. code-block:: sh

    opentelemetry-instrument --propagator gcp_trace <command> <args>

API
---
"""

import re
import typing

import opentelemetry.trace as trace
from opentelemetry.context.context import Context
from opentelemetry.propagators import textmap
from opentelemetry.trace.span import SpanContext, TraceFlags, format_trace_id

_TRACE_CONTEXT_HEADER_NAME = "x-cloud-trace-context"
_TRACE_CONTEXT_HEADER_FORMAT = r"(?P<trace_id>[0-9a-f]{32})\/(?P<span_id>[\d]{1,20})(;o=(?P<trace_flags>\d+))?"
_TRACE_CONTEXT_HEADER_RE = re.compile(_TRACE_CONTEXT_HEADER_FORMAT)
_FIELDS = {_TRACE_CONTEXT_HEADER_NAME}


class CloudTraceFormatPropagator(textmap.TextMapPropagator):
    """This class is for injecting into a carrier the SpanContext in Google
    Cloud format, or extracting the SpanContext from a carrier using Google
    Cloud format.
    """

    @staticmethod
    def _get_header_value(
        getter: textmap.Getter,
        carrier: textmap.CarrierT,
    ) -> typing.Optional[str]:
        # first try all lowercase header
        header = getter.get(carrier, _TRACE_CONTEXT_HEADER_NAME)
        if header:
            return header[0]

        # otherwise try to find in keys for mixed case
        for key in getter.keys(carrier):
            if key.lower() == _TRACE_CONTEXT_HEADER_NAME:
                header = getter.get(carrier, key)
                if header:
                    return header[0]
        return None

    def extract(
        self,
        carrier: textmap.CarrierT,
        context: typing.Optional[Context] = None,
        getter: textmap.Getter = textmap.default_getter,
    ) -> Context:
        if context is None:
            context = Context()

        header = self._get_header_value(getter, carrier)

        if not header:
            return context

        match = re.fullmatch(_TRACE_CONTEXT_HEADER_RE, header)
        if match is None:
            return context

        trace_id = match.group("trace_id")
        span_id = match.group("span_id")
        trace_options = match.group("trace_flags") or "0"

        if trace_id == "0" * 32 or int(span_id) == 0:
            return context

        span_context = SpanContext(
            trace_id=int(trace_id, 16),
            span_id=int(span_id),
            is_remote=True,
            trace_flags=TraceFlags(trace_options),
        )
        return trace.set_span_in_context(
            trace.NonRecordingSpan(span_context), context
        )

    def inject(
        self,
        carrier: textmap.CarrierT,
        context: typing.Optional[Context] = None,
        setter: textmap.Setter = textmap.default_setter,
    ) -> None:
        span = trace.get_current_span(context)
        span_context = span.get_span_context()
        if span_context == trace.INVALID_SPAN_CONTEXT:
            return

        header = "{}/{};o={}".format(
            format_trace_id(span_context.trace_id),
            span_context.span_id,
            int(span_context.trace_flags.sampled),
        )
        setter.set(carrier, _TRACE_CONTEXT_HEADER_NAME, header)

    @property
    def fields(self) -> typing.Set[str]:
        return _FIELDS


class CloudTraceOneWayPropagator(CloudTraceFormatPropagator):
    """This class extracts Trace Context in the Google Cloud format, but does
    not inject this header. It is intended for use in a Composite Propagator to
    inject context in a different format than was received.
    """

    def inject(
        self,
        carrier: textmap.CarrierT,
        context: typing.Optional[Context] = None,
        setter: textmap.Setter = textmap.default_setter,
    ) -> None:
        return

    @property
    def fields(self) -> typing.Set[str]:
        return set()
