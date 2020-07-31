Cloud Trace Propagator Example
==============================

These examples show how to make OpenTelemetry use the 'X-Cloud-Trace-Context' header for context propagation.


Basic Example
-------------

To use this feature you first need to:
    * Create a Google Cloud project. You can `create one here <https://console.cloud.google.com/projectcreate>`_.
    * Enable Cloud Trace API (listed in the Cloud Console as Stackdriver Trace API) in the project `here <https://console.cloud.google.com/apis/library?q=cloud%20trace&filter=visibility:public>`_. If the page says "API Enabled" then you're done! No need to do anything.
    * Enable Default Application Credentials by creating setting `GOOGLE_APPLICATION_CREDENTIALS <https://cloud.google.com/docs/authentication/getting-started>`_ or by `installing gcloud sdk <https://cloud.google.com/sdk/install>`_ and calling ``gcloud auth application-default login``.

* Installation

.. code-block:: sh

    pip install opentelemetry-api
    pip install opentelemetry-sdk
    pip install opentelemetry-ext-google-cloud

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
