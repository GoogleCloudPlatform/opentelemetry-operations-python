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

"""
This module contains OpenTelemetry propagators with support for the Cloud Trace
`X-Cloud-Trace-Context`_ format.

It is recommended to use :class:`CompositeCloudTraceW3CPropagator`, which
combines the default OpenTelemetry supported propagation mechanisms (`W3C
TraceContext <https://www.w3.org/TR/trace-context/>`_ and `Baggage
<https://www.w3.org/TR/baggage/>`_) with :class:`CloudTraceFormatPropagator`.
This way, your application will be able to propagate context to and from Google
and non-Google services.

See :ref:`flask-e2e` for a full example using this propagator.

Usage
-----

.. code-block:: python

    from opentelemetry.propagate import set_global_textmap
    from opentelemetry.propagators.cloud_trace_propagator import (
        CompositeCloudTraceW3CPropagator,
    )

    # set as the global OpenTelemetry propagator
    set_global_textmap(CompositeCloudTraceW3CPropagator())

.. _X-Cloud-Trace-Context: https://cloud.google.com/trace/docs/setup#force-trace
"""

import re
import typing
import logging

import opentelemetry.trace as trace
from opentelemetry.baggage.propagation import W3CBaggagePropagator
from opentelemetry.context.context import Context
from opentelemetry.propagators import textmap
from opentelemetry.trace.span import SpanContext, TraceFlags, format_trace_id
from opentelemetry.propagators import composite, textmap
from opentelemetry.trace.propagation import (
    get_current_span,
    set_span_in_context,
)
from opentelemetry.trace.propagation.tracecontext import (
    TraceContextTextMapPropagator,
)
from opentelemetry.trace.span import (
    INVALID_SPAN,
    DEFAULT_TRACE_STATE,
    INVALID_SPAN_CONTEXT,
    SpanContext,
    TraceFlags,
    format_trace_id,
)

_TRACE_CONTEXT_HEADER_NAME = "x-cloud-trace-context"
_TRACE_CONTEXT_HEADER_FORMAT = r"(?P<trace_id>[0-9a-f]{32})\/(?P<span_id>[\d]{1,20});o=(?P<trace_flags>\d+)"
_TRACE_CONTEXT_HEADER_RE = re.compile(_TRACE_CONTEXT_HEADER_FORMAT)
_FIELDS = {_TRACE_CONTEXT_HEADER_NAME}

logger = logging.getLogger(__name__)


class CloudTraceW3CPropagator(textmap.TextMapPropagator):
    """Propagator to support both OTel W3C defaults and `X-Cloud-Trace-Context`_
    format.

    We recommend using this propagator to support a wide range of propagation
    scenarios. This propagator combines the output of:

    - W3C Trace Context propagator
    - W3C Baggage propagator
    - Cloud Trace format propagator

    If the trace and span IDs output by W3C Trace Context and
    `X-Cloud-Trace-Context`_ match, the TraceFlags and TraceState are merged as
    well.

    .. _X-Cloud-Trace-Context: https://cloud.google.com/trace/docs/setup#force-trace
    """

    def __init__(self) -> None:
        self._trace_context_propagator = TraceContextTextMapPropagator()
        self._baggage_propagator = W3CBaggagePropagator()
        self._cloud_trace_propagator = CloudTraceFormatPropagator()

    def extract(
        self,
        carrier: textmap.CarrierT,
        context: typing.Optional[Context] = None,
        getter: textmap.Getter = textmap.default_getter,
    ) -> Context:
        w3c_context = self._trace_context_propagator.extract(
            carrier, context, getter
        )
        w3c_context = self._baggage_propagator.extract(
            carrier, w3c_context, getter
        )
        cloud_trace_context = self._cloud_trace_propagator.extract(
            carrier, w3c_context, getter
        )

        traceparent_span_context = get_current_span(
            w3c_context
        ).get_span_context()
        cloud_trace_span_context = get_current_span(
            cloud_trace_context
        ).get_span_context()

        combined_context = cloud_trace_context

        # If the cloud trace and w3c span contexts have the same trace and span
        # IDs, merge in w3c trace flags and trace state
        if (
            traceparent_span_context is not INVALID_SPAN_CONTEXT
            and cloud_trace_span_context is not INVALID_SPAN_CONTEXT
        ):
            if (
                traceparent_span_context.trace_id
                == cloud_trace_span_context.trace_id
                and traceparent_span_context.span_id
                == cloud_trace_span_context.span_id
            ):
                combined_context = trace.set_span_in_context(
                    trace.NonRecordingSpan(
                        SpanContext(
                            trace_id=cloud_trace_span_context.trace_id,
                            span_id=cloud_trace_span_context.span_id,
                            is_remote=True,
                            trace_flags=TraceFlags(
                                cloud_trace_span_context.trace_flags
                                | traceparent_span_context.trace_flags
                            ),
                            trace_state=traceparent_span_context.trace_state,
                        )
                    ),
                    combined_context,
                )
            else:
                logger.warning(
                    "Trace and span IDs from traceparent and cloud trace propagators do not match. "
                    "Using the value from cloud trace propagator."
                )

        return context

    def inject(
        self,
        carrier: textmap.CarrierT,
        context: typing.Optional[Context] = None,
        setter: textmap.Setter = textmap.default_setter,
    ) -> None:
        for propagator in (
            self._trace_context_propagator,
            self._baggage_propagator,
            self._cloud_trace_propagator,
        ):
            propagator.inject(carrier=carrier, context=context, setter=setter)


class CloudTraceFormatPropagator(textmap.TextMapPropagator):
    """This class is for injecting into a carrier the SpanContext in Google
    Cloud format, or extracting the SpanContext from a carrier using Google
    Cloud format.
    """

    @staticmethod
    def _get_header_value(
        getter: textmap.Getter, carrier: textmap.CarrierT,
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
        trace_options = match.group("trace_flags")

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
