OpenTelemetry Google Cloud Configurator
========================================

Purpose
-------
Simplifies configuring the Open Telemetry library to write to Google Cloud Observability backends. 


Usage
-----

There are two ways that this can be used:

  1. With automatic instrumentation.
  2. With manual instrumentation.


Automatic Instrumentation
^^^^^^^^^^^^^^^^^^^^^^^^^

To use this component with automatic instrumentation, simply invoke
``opentelemetry-instrument`` with the argument ``--configurator=gcp``.

::

    opentelemetry-instrument \
      --configurator=gcp \
      python \
      the/path/to/your/code.py

See `Python zero-code instrumentation for Python <https://opentelemetry.io/docs/zero-code/python/>`_


Manual Instrumentation
^^^^^^^^^^^^^^^^^^^^^^

You can also call the configurator code manually.

::

    from opentelemetry.configurator.gcp import OpenTelemetryGcpConfigurator

    OpenTelemetryGcpConfigurator().configure()


Installation
------------

You can use a standard Python package management tool like ``pip`` or ``uv`` to install.

The PyPi package is ``opentelemetry-configurator-gcp``.

For the automatic instrumentation, you must additionally install ``opentelemetry-distro``.


References
----------

* `Python zero-code instrumentation for Python <https://opentelemetry.io/docs/zero-code/python/>`_
* `Google Cloud Observability <https://cloud.google.com/stackdriver/docs>`_
