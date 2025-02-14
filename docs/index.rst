.. Google Cloud OpenTelemetry documentation main file, created by
   sphinx-quickstart on Fri Jul 17 19:47:46 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Google Cloud OpenTelemetry's documentation!
======================================================

.. image:: https://badge.fury.io/py/opentelemetry-exporter-gcp-trace.svg
    :target: https://badge.fury.io/py/opentelemetry-exporter-gcp-trace

.. image:: https://badge.fury.io/py/opentelemetry-exporter-gcp-monitoring.svg
    :target: https://badge.fury.io/py/opentelemetry-exporter-gcp-monitoring

.. image:: https://badge.fury.io/py/opentelemetry-resourcedetector-gcp.svg
    :target: https://badge.fury.io/py/opentelemetry-resourcedetector-gcp

.. image:: https://badge.fury.io/py/opentelemetry-propagator-gcp.svg
    :target: https://badge.fury.io/py/opentelemetry-propagator-gcp

This documentation describes OpenTelemetry Python exporters, propagators, and
resource detectors for Google Cloud Platform. Development for these packages
takes place on `Github
<https://github.com/GoogleCloudPlatform/opentelemetry-operations-python>`_.

To get started with instrumentation in Google Cloud, see `Generate traces and metrics with
Python <https://cloud.google.com/stackdriver/docs/instrumentation/setup/python>`_.

To learn more about instrumentation and observability, including opinionated recommendations
for Google Cloud Observability, visit `Instrumentation and observability
<https://cloud.google.com/stackdriver/docs/instrumentation/overview>`_.

Installation
------------

To install the Cloud Trace exporter:

.. code-block:: bash

    pip install opentelemetry-exporter-gcp-trace

To install Cloud Monitoring exporter:

.. code-block:: bash

    pip install opentelemetry-exporter-gcp-monitoring

To install the GCP resource detector:

.. code-block:: bash

    pip install opentelemetry-resourcedetector-gcp

To install the GCP trace propagator:

.. code-block:: bash

    pip install opentelemetry-propagator-gcp


.. toctree::
   :maxdepth: 1
   :caption: Exporters
   :name: exporters
   :glob:

   cloud_monitoring/**
   cloud_trace/**


.. toctree::
   :maxdepth: 1
   :caption: Examples
   :name: examples
   :glob:

   examples/**


.. toctree::
   :hidden:

   apireference

:ref:`apireference`



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
