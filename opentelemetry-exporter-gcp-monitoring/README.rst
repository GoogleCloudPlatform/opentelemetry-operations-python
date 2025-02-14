OpenTelemetry Google Cloud Monitoring Exporter
==============================================

.. image:: https://badge.fury.io/py/opentelemetry-exporter-gcp-monitoring.svg
    :target: https://badge.fury.io/py/opentelemetry-exporter-gcp-monitoring

.. image:: https://readthedocs.org/projects/google-cloud-opentelemetry/badge/?version=latest
    :target: https://google-cloud-opentelemetry.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

This library provides support for exporting metrics to Google Cloud
Monitoring.

To get started with instrumentation in Google Cloud, see `Generate traces and metrics with
Python <https://cloud.google.com/stackdriver/docs/instrumentation/setup/python>`_.

To learn more about instrumentation and observability, including opinionated recommendations
for Google Cloud Observability, visit `Instrumentation and observability
<https://cloud.google.com/stackdriver/docs/instrumentation/overview>`_.

For resource detection and GCP trace context propagation, see
`opentelemetry-tools-google-cloud
<https://pypi.org/project/opentelemetry-tools-google-cloud/>`_. For the
Google Cloud Trace exporter, see `opentelemetry-exporter-gcp-trace
<https://pypi.org/project/opentelemetry-exporter-gcp-trace/>`_.

Installation
------------

.. code:: bash

    pip install opentelemetry-exporter-gcp-monitoring

Usage
-----

.. code:: python

    import time

    from opentelemetry import metrics
    from opentelemetry.exporter.cloud_monitoring import (
        CloudMonitoringMetricsExporter,
    )
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource

    metrics.set_meter_provider(
        MeterProvider(
            metric_readers=[
                PeriodicExportingMetricReader(
                    CloudMonitoringMetricsExporter(), export_interval_millis=5000
                )
            ],
            resource=Resource.create(
                {
                    "service.name": "basic_metrics",
                    "service.namespace": "examples",
                    "service.instance.id": "instance123",
                }
            ),
        )
    )
    meter = metrics.get_meter(__name__)

    # Creates metric workload.googleapis.com/request_counter with monitored resource generic_task
    requests_counter = meter.create_counter(
        name="request_counter",
        description="number of requests",
        unit="1",
    )

    staging_labels = {"environment": "staging"}

    for i in range(20):
        requests_counter.add(25, staging_labels)
        time.sleep(5)


References
----------

* `Cloud Monitoring <https://cloud.google.com/monitoring>`_
* `OpenTelemetry Project <https://opentelemetry.io/>`_
