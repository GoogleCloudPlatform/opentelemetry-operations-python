.. Google Cloud OpenTelemetry documentation master file, created by
   sphinx-quickstart on Fri Jul 17 19:47:46 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Google Cloud OpenTelemetry's documentation!
======================================================

.. image:: https://badge.fury.io/py/opentelemetry-ext-google-cloud.svg
    :target: https://badge.fury.io/py/opentelemetry-ext-google-cloud

This documentation describes OpenTelemetry Python exporters, propagators, and
resource detectors for Google Cloud Platform. Development for these packages
takes place on `Github
<https://github.com/GoogleCloudPlatform/opentelemetry-operations-python>`_.

Installation
------------

.. code-block:: bash

    pip install opentelemetry-ext-google-cloud


.. toctree::
   :maxdepth: 1
   :caption: Exporters
   :name: exporters

   cloud_monitoring/cloud_monitoring
   cloud_trace/cloud_trace


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
