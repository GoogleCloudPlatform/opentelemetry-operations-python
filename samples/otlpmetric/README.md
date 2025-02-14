### OTLP Export Sample with GCP Auth
This example shows how to send metrics to an OTLP (OpenTelemetry Protocol) endpoint that is protected by GCP authentication. The sample showcases the metric export using gRPC.

#### Installation
Install the dependencies and libraries required to run the samples:

```sh
# Move to the sample repository
cd samples/otlpmetric

pip install -r requirements.txt
```

#### Prerequisites
Get Google credentials on your machine:

```sh
gcloud auth application-default login
```

#### Run the Sample
```sh
# export necessary OTEL environment variables
export PROJECT_ID=<project-id>
export OTEL_EXPORTER_OTLP_ENDPOINT=<endpoint>
export OTEL_RESOURCE_ATTRIBUTES="gcp.project_id=$PROJECT_ID,service.name=otlp-sample,service.instance.id=1"

# from the samples/otlpmetric repository
python3 example.py
```
