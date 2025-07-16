# OpenTelemetry ADK instrumentation example

<!-- TODO: link to devsite doc once it is published -->

This sample is an ADK agent instrumented with OpenTelemetry to send traces and logs with GenAI
prompts and responses, and metrics to Google Cloud Observability.

The Agent is a SQL expert that has full access to an ephemeral SQLite database. The database is
initially empty.

## APIs and Permissions

Enable the relevant Cloud Observability APIs if they aren't already enabled.
```sh
gcloud services enable aiplatform.googleapis.com telemetry.googleapis.com logging.googleapis.com monitoring.googleapis.com cloudtrace.googleapis.com
```

This sample writes to Cloud Logging, Cloud Monitoring, and Cloud Trace. Grant yourself the
following roles to run the example:
- `roles/logging.logWriter` – see https://cloud.google.com/logging/docs/access-control#permissions_and_roles
- `roles/monitoring.metricWriter` – see https://cloud.google.com/monitoring/access-control#predefined_roles
- `roles/telemetry.writer` – see https://cloud.google.com/trace/docs/iam#telemetry-roles

## Running the example

The sample can easily be run in Cloud Shell. You can also use
[Application Default Credentials][ADC] locally. Clone and set environment variables:
```sh
git clone https://github.com/GoogleCloudPlatform/opentelemetry-operations-python.git
cd opentelemetry-operations-python/samples/adk-sql-agent
```

Configure the environment and run the sample:
```sh
python -m venv venv/
source venv/bin/activate
pip install -r requirements.txt
env $(cat opentelemetry.env | xargs) python main.py
```

Alternatively if you have [`uv`](https://docs.astral.sh/uv/) installed:

```sh
uv run --env-file opentelemetry.env main.py
```

## Viewing the results

To view the generated traces with [Generative AI
events](https://cloud.google.com/trace/docs/finding-traces#view_generative_ai_events) in the
GCP console, use the [Trace Explorer](https://cloud.google.com/trace/docs/finding-traces). Filter for spans with OpenTelemetry Service: `adk-sql-agent`.

[ADC]: https://cloud.google.com/docs/authentication/application-default-credentials
