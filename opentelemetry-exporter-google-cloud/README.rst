OpenTelemetry Google Cloud Integration
======================================

.. image:: https://badge.fury.io/py/opentelemetry-exporter-google-cloud.svg
    :target: https://badge.fury.io/py/opentelemetry-exporter-google-cloud

.. image:: https://readthedocs.org/projects/google-cloud-opentelemetry/badge/?version=latest
    :target: https://google-cloud-opentelemetry.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

This library provides support for:

- Exporting traces to Google Cloud Trace
- Exporting metrics to Google Cloud Monitoring

For resource detection and GCP trace context propagation, see
`opentelemetry-tools-google-cloud
<https://pypi.org/project/opentelemetry-tools-google-cloud/>`_.

Installation
------------

.. code:: bash

    pip install opentelemetry-exporter-google-cloud

Usage
-----

Traces

.. code:: python

    from opentelemetry import trace
    from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        SimpleExportSpanProcessor,
    )

    trace.set_tracer_provider(TracerProvider())

    cloud_trace_exporter = CloudTraceSpanExporter(
        project_id='my-gcloud-project',
    )
    trace.get_tracer_provider().add_span_processor(
        SimpleExportSpanProcessor(cloud_trace_exporter)
    )
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span('foo'):
        print('Hello world!')


Metrics

.. code:: python

    import time

    from opentelemetry import metrics
    from opentelemetry.exporter.cloud_monitoring import (
        CloudMonitoringMetricsExporter,
    )
    from opentelemetry.sdk.metrics import Counter, MeterProvider

    metrics.set_meter_provider(MeterProvider())
    meter = metrics.get_meter(__name__)
    metrics.get_meter_provider().start_pipeline(
        meter, CloudMonitoringMetricsExporter(), 5
    )

    requests_counter = meter.create_metric(
        name="request_counter",
        description="number of requests",
        unit="1",
        value_type=int,
        metric_type=Counter,
        label_keys=("environment"),
    )

    staging_labels = {"environment": "staging"}

    for i in range(20):
        requests_counter.add(25, staging_labels)
        time.sleep(10)



References
----------

* `Cloud Trace <https://cloud.google.com/trace/>`_
* `OpenTelemetry Project <https://opentelemetry.io/>`_
