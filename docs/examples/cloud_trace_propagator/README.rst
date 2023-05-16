Cloud Trace Propagator Example
==============================

These examples show how to make OpenTelemetry use the
``X-Cloud-Trace-Context`` header for context propagation.


Basic Example
-------------

To use this feature you first need to:

* Create a Google Cloud project. You can `create one here <https://console.cloud.google.com/projectcreate>`_.
* Enable `Application Default Credentials
  <https://cloud.google.com/docs/authentication/provide-credentials-adc>`_ by `installing
  gcloud <https://cloud.google.com/sdk/install>`_ and running ``gcloud auth
  application-default login``.


* Installation

.. code-block:: sh

    pip install opentelemetry-api \
      opentelemetry-sdk \
      opentelemetry-instrumentation-flask \
      opentelemetry-instrumentation-requests \
      opentelemetry-exporter-gcp-trace \
      opentelemetry-propagator-gcp \
      Flask

* Create a server that uses the Cloud Trace header

.. literalinclude:: server.py
    :language: python
    :lines: 1-

* Make a client that uses the Cloud Trace header

.. literalinclude:: client.py
    :language: python
    :lines: 1-


Checking Output
--------------------------

After running these examples, you can go to `Cloud Trace overview <https://console.cloud.google.com/traces/list>`_ to see the results.
