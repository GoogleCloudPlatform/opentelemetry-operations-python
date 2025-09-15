OpenTelemetry GCP Credential Provider for OTLP Exporters
==============================================

.. image:: https://badge.fury.io/py/opentelemetry-exporter-gcp-logging.svg
    :target: https://badge.fury.io/py/opentelemetry-exporter-gcp-logging

.. image:: https://readthedocs.org/projects/google-cloud-opentelemetry/badge/?version=latest
    :target: https://google-cloud-opentelemetry.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

This library provides support for supplying your machine's Application Default Credentials (https://cloud.google.com/docs/authentication/application-default-credentials)
to the OTLP Exporters created automatically by OTEL Python's auto instrumentation.
These credentials allow telemetry to be sent to `telemetry.googleapis.com`.


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

Your installed HTTP/GRPC OTLP Exporter must be at release `>=1.37` for this feature.

Set the following environment variables:
`export OTEL_RESOURCE_ATTRIBUTES="gcp.project_id=<project-id>"`
`export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT="https://telemetry.googleapis.com:443/v1/traces"`

If you plan to have python auto instrumentation use the GRPC OTLP Exporter to send traces to Cloud Trace:
`export OTEL_PYTHON_EXPORTER_OTLP_GRPC_TRACES_CREDENTIAL_PROVIDER=gcp_grpc_credentials`

If you plan to have python auto instrumentation use the HTTP OTLP Exporter to send traces to Cloud Trace:
`export OTEL_PYTHON_EXPORTER_OTLP_HTTP_TRACES_CREDENTIAL_PROVIDER=gcp_http_credentials`


References
----------

* `Cloud Logging <https://cloud.google.com/logging>`_
* `OpenTelemetry Project <https://opentelemetry.io/>`_
