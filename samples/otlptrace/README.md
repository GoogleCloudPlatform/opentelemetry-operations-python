### OTLP Export Sample with GCP Auth
This example shows how to send traces to an OTLP (OpenTelemetry Protocol) endpoint that is protected by GCP authentication. The sample showcases the trace export using:
 - gRPC
 - http with protobuf

#### Installation
Install the dependencies and libraries required to run the samples:

```sh
# Move to the sample repository
cd samples/otlptrace

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
export OTEL_RESOURCE_ATTRIBUTES="gcp.project_id=<project-id>"
export OTEL_EXPORTER_OTLP_ENDPOINT=<endpoint>

cd samples/otlptrace && python3 example_grpc.py
```
Other variations of the sample:
 - `python3 example_http.py` - will run a program that will export traces using http/protobuf.
