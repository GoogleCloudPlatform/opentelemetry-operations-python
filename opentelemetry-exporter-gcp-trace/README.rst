OpenTelemetry Google Cloud Integration
======================================

.. image:: https://badge.fury.io/py/opentelemetry-exporter-gcp-trace.svg
    :target: https://badge.fury.io/py/opentelemetry-exporter-gcp-trace

.. image:: https://readthedocs.org/projects/google-cloud-opentelemetry/badge/?version=latest
    :target: https://google-cloud-opentelemetry.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

This library provides support for exporting traces to Google Cloud Trace.

For resource detection and GCP trace context propagation, see
`opentelemetry-tools-google-cloud
<https://pypi.org/project/opentelemetry-tools-google-cloud/>`_. For the
Google Cloud Monitoring exporter, see
`opentelemetry-exporter-gcp-monitoring
<https://pypi.org/project/opentelemetry-exporter-gcp-monitoring/>`_.

Installation
------------

.. code:: bash

    pip install opentelemetry-exporter-gcp-trace

Usage
-----

.. code:: python

    from opentelemetry import trace
    from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        SimpleSpanProcessor,
    )

    trace.set_tracer_provider(TracerProvider())

    cloud_trace_exporter = CloudTraceSpanExporter(
        project_id='my-gcloud-project',
    )
    trace.get_tracer_provider().add_span_processor(
        SimpleSpanProcessor(cloud_trace_exporter)
    )
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span('foo'):
        print('Hello world!')


References
----------

* `Cloud Trace <https://cloud.google.com/trace/>`_
* `OpenTelemetry Project <https://opentelemetry.io/>`_
