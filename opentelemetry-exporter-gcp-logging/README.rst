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
    import logging
    from opentelemetry.exporter.cloud_logging import (
        CloudLoggingExporter,
    )
    from opentelemetry.sdk.resources import Resource
    from opentelemetry._logs import set_logger_provider
    from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
    from opentelemetry.sdk._logs.export import BatchLogRecordProcessor

    logger_provider = LoggerProvider(
        resource=Resource.create(
            {
                "service.name": "shoppingcart",
                "service.instance.id": "instance-12",
            }
        ),
    )
    set_logger_provider(logger_provider)
    exporter = CloudLoggingExporter(default_log_name='my_log')
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(exporter))
    handler = LoggingHandler(level=logging.ERROR, logger_provider=logger_provider)

    # Attach OTLP handler to root logger
    logging.getLogger().addHandler(handler)

    # Create namespaced logger
    # It is recommended to not use the root logger with OTLP handler
    # so telemetry is collected only for the application
    logger1 = logging.getLogger("myapp.area1")

    logger1.error({'structured_log_will_go_to_json_payload': 'value'}, extra={'this_will_go_to_LogEntry_labels_field': 'value'})

References
----------

* `Cloud Logging <https://cloud.google.com/logging>`_
* `OpenTelemetry Project <https://opentelemetry.io/>`_
