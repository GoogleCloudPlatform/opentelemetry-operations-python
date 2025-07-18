OpenTelemetry GCP Credential Provider for OTLP Exporters
==============================================

.. image:: https://badge.fury.io/py/opentelemetry-exporter-gcp-logging.svg
    :target: https://badge.fury.io/py/opentelemetry-exporter-gcp-logging

.. image:: https://readthedocs.org/projects/google-cloud-opentelemetry/badge/?version=latest
    :target: https://google-cloud-opentelemetry.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

This library provides support for supplying GCP authentication credentials to Python's auto instrumentation/


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

    pip install opentelemetry-gcp-auth-provider

Usage
-----

Set the following environment variables:
`export OTEL_RESOURCE_ATTRIBUTES="gcp.project_id=<project-id>"`

To have python auto instrumentation use the HTTP OTLP Exporter to send traces to Cloud Trace:
`SET`

To have python auto instrumentation use the GRPC OTLP Exporter to send traces to Cloud Trace:
''



References
----------

* `Cloud Logging <https://cloud.google.com/logging>`_
* `OpenTelemetry Project <https://opentelemetry.io/>`_
