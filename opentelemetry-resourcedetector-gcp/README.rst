OpenTelemetry Google Cloud Resource Detector
============================================

.. image:: https://badge.fury.io/py/opentelemetry-resourcedetector-gcp.svg
    :target: https://badge.fury.io/py/opentelemetry-resourcedetector-gcp

.. image:: https://readthedocs.org/projects/google-cloud-opentelemetry/badge/?version=latest
    :target: https://google-cloud-opentelemetry.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

This library provides support for detecting GCP resources like GCE, GKE, etc.

To get started with instrumentation in Google Cloud, see `Generate traces and metrics with
Python <https://cloud.google.com/stackdriver/docs/instrumentation/setup/python>`_.

To learn more about instrumentation and observability, including opinionated recommendations
for Google Cloud Observability, visit `Instrumentation and observability
<https://cloud.google.com/stackdriver/docs/instrumentation/overview>`_.

Installation
------------

.. code:: bash

    pip install opentelemetry-resourcedetector-gcp

Usage
-----

.. code:: python

    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry import trace
    from opentelemetry.sdk.resources import SERVICE_INSTANCE_ID, Resource

    # This will use the GooglecloudResourceDetector under the covers.
    resource = Resource.create(
        attributes={
            # Use the PID as the service.instance.id to avoid duplicate timeseries
            # from different Gunicorn worker processes.
            SERVICE_INSTANCE_ID: f"worker-{os.getpid()}",
        }
    )
    traceProvider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(OTLPSpanExporter())
    traceProvider.add_span_processor(processor)
    trace.set_tracer_provider(traceProvider)

References
----------

* `Cloud Monitoring <https://cloud.google.com/monitoring>`_
* `OpenTelemetry Project <https://opentelemetry.io/>`_
