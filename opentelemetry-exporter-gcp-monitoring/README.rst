OpenTelemetry Google Cloud Monitoring Exporter
==============================================

.. image:: https://badge.fury.io/py/opentelemetry-exporter-gcp-monitoring.svg
    :target: https://badge.fury.io/py/opentelemetry-exporter-gcp-monitoring

.. image:: https://readthedocs.org/projects/google-cloud-opentelemetry/badge/?version=latest
    :target: https://google-cloud-opentelemetry.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

This library provides support for exporting metrics to Google Cloud
Monitoring.

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
    from opentelemetry.sdk.metrics import Counter, MeterProvider

    metrics.set_meter_provider(MeterProvider())
    meter = metrics.get_meter(__name__)
    metrics.get_meter_provider().start_pipeline(
        meter, CloudMonitoringMetricsExporter(), 5
    )

    requests_counter = meter.create_counter(
        name="request_counter",
        description="number of requests",
        unit="1",
        value_type=int
    )

    staging_labels = {"environment": "staging"}

    for i in range(20):
        requests_counter.add(25, staging_labels)
        time.sleep(10)



References
----------

* `Cloud Monitoring <https://cloud.google.com/monitoring>`_
* `OpenTelemetry Project <https://opentelemetry.io/>`_
