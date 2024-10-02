OpenTelemetry Google Cloud Propagator
======================================

.. image:: https://badge.fury.io/py/opentelemetry-propagator-gcp.svg
    :target: https://badge.fury.io/py/opentelemetry-propagator-gcp

.. image:: https://readthedocs.org/projects/google-cloud-opentelemetry/badge/?version=latest
    :target: https://google-cloud-opentelemetry.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

This library provides support for propagating trace context in the Google
Cloud ``X-Cloud-Trace-Context`` format.

To get started with instrumentation in Google Cloud, see `Generate traces and metrics with
Python <https://cloud.google.com/stackdriver/docs/instrumentation/setup/python>`_.

To learn more about instrumentation and observability, including opinionated recommendations
for Google Cloud Observability, visit `Instrumentation and observability
<https://cloud.google.com/stackdriver/docs/instrumentation/overview>`_.

Installation
------------

.. code:: bash

    pip install opentelemetry-propagator-gcp

Usage
-----

The ``CloudTraceOneWayPropagator`` reads the Google Cloud
``X-Cloud-Trace-Context`` format, but does not write the
``X-Cloud-Trace-Context`` header on outgoing requests. It is intended for use
with a CompositePropagator as below.

.. code-block:: python

    from opentelemetry.propagate import set_global_textmap
    from opentelemetry.propagators.composite import CompositePropagator
    from opentelemetry.propagators.cloud_trace_propagator import (
        CloudTraceOneWayPropagator,
    )
    set_global_textmap(
        CompositePropagator([
            CloudTraceOneWayPropagator(),
            propagate.get_global_textmap(),
        ]),
    )

The ``CloudTraceFormatPropagator`` reads and writes the
``X-Cloud-Trace-Context`` header formats. Note that when using this propagator,
the ``sampled`` bit is interpreted as the ``TRACE_TRUE`` flag, which may cause a
higher sampling rate than desired. See the `Trace documentation
<https://cloud.google.com/trace/docs/setup#force-trace>` for additional context.

.. code-block:: python

    from opentelemetry.propagate import set_global_textmap
    from opentelemetry.propagators.cloud_trace_propagator import (
        CloudTraceFormatPropagator,
    )

    # Set the X-Cloud-Trace-Context header
    set_global_textmap(CloudTraceFormatPropagator())
.. code-block:: python

    from opentelemetry.propagate import set_global_textmap
    from opentelemetry.propagators.cloud_trace_propagator import (
        CloudTraceFormatPropagator,
    )

    # Set the X-Cloud-Trace-Context header
    set_global_textmap(CloudTraceFormatPropagator())


References
----------

* `Cloud Trace <https://cloud.google.com/trace/>`_
* `OpenTelemetry Project <https://opentelemetry.io/>`_
