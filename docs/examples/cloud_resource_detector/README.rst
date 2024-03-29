Cloud Resources Detector Example
================================

These examples show how to use OpenTelemetry to detect resource information and
send it to Cloud Trace or Cloud Monitoring.


Basic Example
-------------

To use this feature you first need to:

* Create a Google Cloud project. You can `create one here <https://console.cloud.google.com/projectcreate>`_.
* Set up `Application Default Credentials
  <https://cloud.google.com/docs/authentication/provide-credentials-adc>`_ by `installing
  gcloud <https://cloud.google.com/sdk/install>`_ and running ``gcloud auth
  application-default login``.
* Setup a Google tool like `Google Compute Engine <https://cloud.google.com/compute/docs/quickstart-linux>`_ (GCE) or `Google Kubernetes Engine <https://cloud.google.com/kubernetes-engine/docs/quickstart>`_ (GKE).
* Run the below example in the Google tool.

* Installation

.. code-block:: sh

    pip install opentelemetry-api \
      opentelemetry-sdk \
      opentelemetry-exporter-gcp-trace \
      opentelemetry-exporter-gcp-monitoring \
      opentelemetry-resourcedetector-gcp

* Run an example on the Google tool of your choice

.. literalinclude:: resource_detector_trace.py
    :language: python
    :lines: 1-

.. literalinclude:: resource_detector_metrics.py
    :language: python
    :lines: 1-

Checking Output
--------------------------

After running the metrics example:

* Go to the `Cloud Monitoring Metrics Explorer page <https://console.cloud.google.com/monitoring/metrics-explorer>`_.
* In "Find resource type and metric" enter "OpenTelemetry/request_counter_with_resource".
* You can filter by resource info and change the graphical output here as well.

Or, if you ran the tracing example, you can go to `Cloud Trace overview <https://console.cloud.google.com/traces/list>`_ to see the results.


Troubleshooting
--------------------------

gke_container resources are not being detected or exported:
###########################################################
You need to manually pass in some information via the `Downward API <https://kubernetes.io/docs/tasks/inject-data-application/environment-variable-expose-pod-information/>`_
to enable GKE resource detection. Your kubernetes config file should look
something like this (passing in ``NAMESPACE``, ``CONTAINER_NAME``, ``POD_NAME``)

.. code-block:: yaml

    apiVersion: "apps/v1"
    kind: "Deployment"
    metadata:
      name: "food-find"
    spec:
      replicas: 3
      selector:
        matchLabels:
          app: "food-find"
      template:
        metadata:
          labels:
            app: "food-find"
        spec:
          terminationGracePeriodSeconds: 30
          containers:
          - name: "food-finder"
            image: "gcr.io/aaxue-gke/food-finder:v1"
            imagePullPolicy: "Always"
            env:
                - name: NAMESPACE
                  valueFrom:
                    fieldRef:
                      fieldPath: metadata.namespace
                - name: CONTAINER_NAME
                  value: "food-finder"
                - name: POD_NAME
                  valueFrom:
                    fieldRef:
                      fieldPath: metadata.name
            ports:
            - containerPort: 8080
          hostNetwork: true
          dnsPolicy: Default
