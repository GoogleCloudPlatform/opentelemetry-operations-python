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
#
import unittest

import opentelemetry.trace as trace
from opentelemetry.context import get_current
from opentelemetry.context.context import Context
from opentelemetry.propagators.cloud_trace_propagator import (
    _TRACE_CONTEXT_HEADER_NAME,
    CloudTraceFormatPropagator,
)
from opentelemetry.propagators.textmap import default_getter
from opentelemetry.trace.span import (
    INVALID_SPAN_ID,
    INVALID_TRACE_ID,
    SpanContext,
    TraceFlags,
    format_trace_id,
)


class TestCloudTraceFormatPropagator(unittest.TestCase):
    def setUp(self):
        self.propagator = CloudTraceFormatPropagator()
        self.valid_trace_id = 281017822499060589596062859815111849546
        self.valid_span_id = 17725314949316355921
        self.too_long_id = 111111111111111111111111111111111111111111111

    def _extract(self, header_value):
        """Test helper"""
        header = {_TRACE_CONTEXT_HEADER_NAME: [header_value]}
        new_context = self.propagator.extract(
            carrier=header, getter=default_getter
        )
        return new_context

    def _extract_span_context(self, header_value):
        """Test helper"""
        return trace.get_current_span(
            self._extract(header_value)
        ).get_span_context()

    def _inject(self, span=None):
        """Test helper"""
        ctx = get_current()
        if span is not None:
            ctx = trace.set_span_in_context(span, ctx)
        output = {}
        self.propagator.inject(output, context=ctx)
        return output.get(_TRACE_CONTEXT_HEADER_NAME)

    def _assert_failed_to_extract(self, new_context: Context):
        self.assertEqual(new_context, Context())
        self.assertEqual(
            trace.get_current_span(new_context).get_span_context(),
            trace.INVALID_SPAN.get_span_context(),
        )

    def test_no_context_header(self):
        headers = {}
        new_context = self.propagator.extract(
            carrier=headers, getter=default_getter
        )
        self._assert_failed_to_extract(new_context)

    def test_empty_context_header(self):
        header = ""
        new_context = self._extract(header)
        self._assert_failed_to_extract(new_context)

    def test_valid_header(self):
        header = "{}/{};o=1".format(
            format_trace_id(self.valid_trace_id), self.valid_span_id
        )
        new_span_context = self._extract_span_context(header)
        self.assertEqual(new_span_context.trace_id, self.valid_trace_id)
        self.assertEqual(new_span_context.span_id, self.valid_span_id)
        self.assertEqual(new_span_context.trace_flags, TraceFlags(1))
        self.assertTrue(new_span_context.is_remote)

        header = "{}/{};o=10".format(
            format_trace_id(self.valid_trace_id), self.valid_span_id
        )
        new_span_context = self._extract_span_context(header)
        self.assertEqual(new_span_context.trace_id, self.valid_trace_id)
        self.assertEqual(new_span_context.span_id, self.valid_span_id)
        self.assertEqual(new_span_context.trace_flags, TraceFlags(10))
        self.assertTrue(new_span_context.is_remote)

        header = "{}/{};o=0".format(
            format_trace_id(self.valid_trace_id), self.valid_span_id
        )
        new_span_context = self._extract_span_context(header)
        self.assertEqual(new_span_context.trace_id, self.valid_trace_id)
        self.assertEqual(new_span_context.span_id, self.valid_span_id)
        self.assertEqual(new_span_context.trace_flags, TraceFlags(0))
        self.assertTrue(new_span_context.is_remote)

        header = "{}/{};o=0".format(format_trace_id(self.valid_trace_id), 345)
        new_span_context = self._extract_span_context(header)
        self.assertEqual(new_span_context.trace_id, self.valid_trace_id)
        self.assertEqual(new_span_context.span_id, 345)
        self.assertEqual(new_span_context.trace_flags, TraceFlags(0))
        self.assertTrue(new_span_context.is_remote)

        header = "{}/{}".format(format_trace_id(self.valid_trace_id), 345)
        new_span_context = self._extract_span_context(header)
        self.assertEqual(new_span_context.trace_id, self.valid_trace_id)
        self.assertEqual(new_span_context.span_id, 345)
        self.assertEqual(new_span_context.trace_flags, TraceFlags(0))
        self.assertTrue(new_span_context.is_remote)

    def test_mixed_case_header_key(self):
        header_value = "{}/{};o=1".format(
            format_trace_id(self.valid_trace_id), self.valid_span_id
        )

        for header_key in (
            "X-Cloud-Trace-Context",
            "X-ClOuD-tRace-ConTeXt",
            "X-CLOUD-TRACE-CONTEXT",
        ):
            header_map = {header_key: [header_value]}
            new_context = self.propagator.extract(
                carrier=header_map, getter=default_getter
            )
            new_span_context = trace.get_current_span(
                new_context
            ).get_span_context()
            self.assertEqual(new_span_context.trace_id, self.valid_trace_id)
            self.assertEqual(new_span_context.span_id, self.valid_span_id)
            self.assertEqual(new_span_context.trace_flags, TraceFlags(1))
            self.assertTrue(new_span_context.is_remote)

    def test_invalid_header_format(self):
        header = "invalid_header"
        self._assert_failed_to_extract(self._extract(header))

        header = "{}/{};o=".format(
            format_trace_id(self.valid_trace_id), self.valid_span_id
        )
        self._assert_failed_to_extract(self._extract(header))

        header = "extra_chars/{}/{};o=1".format(
            format_trace_id(self.valid_trace_id), self.valid_span_id
        )
        self._assert_failed_to_extract(self._extract(header))

        header = "{}/{}extra_chars;o=1".format(
            format_trace_id(self.valid_trace_id), self.valid_span_id
        )
        self._assert_failed_to_extract(self._extract(header))

        header = "{}/{};o=1extra_chars".format(
            format_trace_id(self.valid_trace_id), self.valid_span_id
        )
        self._assert_failed_to_extract(self._extract(header))

        header = "{}/;o=1".format(format_trace_id(self.valid_trace_id))
        self._assert_failed_to_extract(self._extract(header))

        header = "/{};o=1".format(self.valid_span_id)
        self._assert_failed_to_extract(self._extract(header))

        header = "{}/{};o={}".format("123", "34", "4")
        self._assert_failed_to_extract(self._extract(header))

    def test_invalid_trace_id(self):
        header = "{}/{};o={}".format(INVALID_TRACE_ID, self.valid_span_id, 1)
        self._assert_failed_to_extract(self._extract(header))

        header = "{}/{};o={}".format("0" * 32, self.valid_span_id, 1)
        self._assert_failed_to_extract(self._extract(header))

        header = "0/{};o={}".format(self.valid_span_id, 1)
        self._assert_failed_to_extract(self._extract(header))

        header = "234/{};o={}".format(self.valid_span_id, 1)
        self._assert_failed_to_extract(self._extract(header))

        header = "{}/{};o={}".format(self.too_long_id, self.valid_span_id, 1)
        self._assert_failed_to_extract(self._extract(header))

    def test_invalid_span_id(self):
        header = "{}/{};o={}".format(
            format_trace_id(self.valid_trace_id), INVALID_SPAN_ID, 1
        )
        self._assert_failed_to_extract(self._extract(header))

        header = "{}/{};o={}".format(
            format_trace_id(self.valid_trace_id), "0" * 16, 1
        )
        self._assert_failed_to_extract(self._extract(header))

        header = "{}/{};o={}".format(
            format_trace_id(self.valid_trace_id), "0", 1
        )
        self._assert_failed_to_extract(self._extract(header))

        header = "{}/{};o={}".format(
            format_trace_id(self.valid_trace_id), self.too_long_id, 1
        )
        self._assert_failed_to_extract(self._extract(header))

    def test_inject_with_no_context(self):
        output = self._inject()
        self.assertIsNone(output)

    def test_inject_with_invalid_context(self):
        output = self._inject(trace.INVALID_SPAN)
        self.assertIsNone(output)

    def test_inject_with_valid_context(self):
        span_context = SpanContext(
            trace_id=self.valid_trace_id,
            span_id=self.valid_span_id,
            is_remote=True,
            trace_flags=TraceFlags(1),
        )
        output = self._inject(trace.NonRecordingSpan(span_context))
        self.assertEqual(
            output,
            "{}/{};o={}".format(
                format_trace_id(self.valid_trace_id),
                self.valid_span_id,
                1,
            ),
        )
