Cloud Trace Exporter Example
============================

These examples show how to use OpenTelemetry to send tracing data to Cloud Trace.


Basic Example
-------------

To use this exporter you first need to:

* Create a Google Cloud project. You can `create one here <https://console.cloud.google.com/projectcreate>`_.
* Set up `Application Default Credentials
  <https://cloud.google.com/docs/authentication/provide-credentials-adc>`_ by `installing
  gcloud <https://cloud.google.com/sdk/install>`_ and running ``gcloud auth
  application-default login``.


* Installation

.. code-block:: sh

    pip install opentelemetry-exporter-gcp-trace \
        opentelemetry-api \
        opentelemetry-sdk

* Run a basic example locally

.. literalinclude:: basic_trace.py
    :language: python
    :lines: 1-

* Run a more advanced example that uses features like attributes, events,
  links, and batching. You should generally use the
  :class:`opentelemetry.sdk.trace.export.BatchSpanProcessor` for real
  production purposes to optimize performance.

.. literalinclude:: advanced_trace.py
    :language: python
    :lines: 1-

Checking Output
--------------------------

After running any of these examples, you can go to `Cloud Trace overview <https://console.cloud.google.com/traces/list>`_ to see the results.


Further Reading
--------------------------

* `More information about exporters in general <https://opentelemetry-python.readthedocs.io/en/stable/getting-started.html#configure-exporters-to-emit-spans-elsewhere>`_

Troubleshooting
--------------------------

Running basic_trace.py hangs:
#############################

* Make sure you've setup Application Default Credentials. Either run ``gcloud auth application-default login`` or set the ``GOOGLE_APPLICATION_CREDENTIALS`` environment variable to be a path to a service account token file.

Getting error ``google.api_core.exceptions.ResourceExhausted: 429 Resource has been exhausted``:
################################################################################################

* Check that you've enabled the `Cloud Trace (Stackdriver Trace) API <https://console.cloud.google.com/apis/library?q=cloud%20trace&filter=visibility:public>`_

bash: pip: command not found:
#############################

* `Install pip <https://cloud.google.com/python/setup#installing_python>`_
* If your machine uses python2 by default, pip will also be the python2 version. Try using ``pip3`` instead of ``pip``.

pip install is hanging
######################
Try upgrading pip

.. code-block:: sh

    pip install --upgrade pip

``pip install grcpio`` may take a long time compiling C extensions when there is no wheel available for your platform, gRPC version, and Python version.

ImportError: No module named opentelemetry
##########################################
Make sure you are using python3. If

.. code-block:: sh

    python --version

returns ``Python 2.X.X`` try calling

.. code-block:: sh

    python3 basic_trace.py


Exporting is slow or making the program slow
############################################
:class:`opentelemetry.sdk.trace.export.SimpleSpanProcessor` will slow
down your program because it exports spans synchronously, one-by-one as they
finish, without any batching. It should only be used for testing or
debugging.

Instead, use :class:`opentelemetry.sdk.trace.export.BatchSpanProcessor`
(with the default parameters) which buffers spans and sends them in batches
in a background thread.

.. code-block:: python

    trace.get_tracer_provider().add_span_processor(
        BatchSpanProcessor(cloud_trace_exporter)
    )
