#! /usr/bin/env python3

import sys

from opentelemetry import trace as otel_trace
from opentelemetry import metrics as otel_metrics
from opentelemetry import _logs as otel_logs


def is_tracer_noop():
    tracer = otel_trace.get_tracer(__name__)
    if isinstance(tracer, otel_trace.ProxyTracer):
        tracer = getattr(tracer, '_tracer')
    return isinstance(tracer, otel_trace.NoOpTracer)


def is_metrics_noop():
   return isinstance(otel_metrics.get_meter_provider(), otel_metrics.NoOpMeterProvider)


def is_logging_noop():
    return isinstance(otel_logs.get_logger_provider(), otel_logs.NoOpLoggerProvider)        


def main():
    signals_to_noop_checker = {
        'trace': is_tracer_noop,
        'metrics': is_metrics_noop,
        'logs': is_logging_noop,
    }
    noop_signals = []
    for signal_name, noop_tester_func in signals_to_noop_checker.items():
        is_noop = noop_tester_func()
        print(f'Signal "{signal_name}" is no-op?: {is_noop}')
        if is_noop:
            noop_signals.append(signal_name)
    if not noop_signals:
        print('All signals successfully configured.')
        return
    noop_count = len(noop_signals)
    total_count = len(signals_to_noop_checker)
    print(f'{noop_count}/{total_count} signals not configured: {noop_signals}')
    sys.exit(1)


if __name__ == '__main__':
    main()
