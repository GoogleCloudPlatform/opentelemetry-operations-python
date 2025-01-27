OpenTelemetry Google Cloud Logging Exporter
==============================================

.. image:: https://badge.fury.io/py/opentelemetry-exporter-gcp-logging.svg
    :target: https://badge.fury.io/py/opentelemetry-exporter-gcp-logging

.. image:: https://readthedocs.org/projects/google-cloud-opentelemetry/badge/?version=latest
    :target: https://google-cloud-opentelemetry.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

This library provides support for exporting logs to Google Cloud
Logging.

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

    pip install opentelemetry-exporter-gcp-logging

Usage
-----

.. code:: python

    from opentelemetry.exporter.cloud_logging import (
        CloudLoggingExporter,
    )
    from opentelemetry.sdk._logs._internal import LogRecord
    from opentelemetry._logs.severity import SeverityNumber
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk._logs import LogData
    from opentelemetry.sdk.util.instrumentation import InstrumentationScope


    exporter = CloudLoggingExporter(default_log_name='my_log')
    exporter.export(
        [
            LogData(
                log_record=LogRecord(
                    resource=Resource({}),
                    timestamp=1736976310997977393,
                    severity_number=SeverityNumber(20),
                    attributes={
                        "gen_ai.system": "openai",
                        "event.name": "gen_ai.system.message",
                    },
                    body={
                        "kvlistValue": {
                            "values": [
                                {
                                    "key": "content",
                                    "value": {"stringValue": "You're a helpful assistant."},
                                }
                            ]
                        }
                    },
                ),
                instrumentation_scope=InstrumentationScope("test"),
            )
        ]
    )


References
----------

* `Cloud Logging <https://cloud.google.com/logging>`_
* `OpenTelemetry Project <https://opentelemetry.io/>`_
