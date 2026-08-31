# Migration Guide

This guide provides instructions on how to migrate from the custom exporters and propagators in this repository to the standard OpenTelemetry OTLP exporters and W3C Trace Context propagator.

## Overview

Google Cloud supports native OTLP (OpenTelemetry Protocol) ingestion for Cloud Trace, Cloud Monitoring, and Cloud Logging via the [Telemetry API](https://docs.cloud.google.com/stackdriver/docs/reference/telemetry/overview). This allows you to use standard OpenTelemetry OTLP exporters for sending telemetry data to Google Cloud. In addition, Google Cloud infrastructure natively supports standard W3C Trace Context headers (`traceparent` and `tracestate`), allowing you to use standard OpenTelemetry context propagation without proprietary headers.

---

## Resource Detection (Recommended for All Signals)

When migrating to OTLP exporters, installing the GCP Resource Detector package ([opentelemetry-resourcedetector-gcp](https://github.com/open-telemetry/opentelemetry-python-contrib/tree/main/resource/opentelemetry-resourcedetector-gcp)) automatically populates Google Cloud resource attributes (such as `gcp.project_id`, `cloud.account.id`, `host.id`, `k8s.pod.name`, etc.) for OpenTelemetry SDK providers (`TracerProvider`, `MeterProvider`, `LoggerProvider`).

### Installation

```bash
pip install opentelemetry-resourcedetector-gcp
```

### Usage & Configuration

* **Manual SDK Setup (In Code):** When manually setting up the SDK in Python (e.g., instantiating `TracerProvider()`, `MeterProvider()`, or `LoggerProvider()`), the GCP resource detector is **automatically discovered and applied** simply by installing `opentelemetry-resourcedetector-gcp`. No additional code changes or environment variables are required.
* **Auto-Instrumentation / Zero-Code:** When using OpenTelemetry auto-instrumentation (`opentelemetry-instrument`), enable the GCP resource detector via the `OTEL_EXPERIMENTAL_RESOURCE_DETECTORS` environment variable:

```bash
export OTEL_EXPERIMENTAL_RESOURCE_DETECTORS="gcp"
```

You can also specify additional resource attributes via `OTEL_RESOURCE_ATTRIBUTES`:

```bash
export OTEL_RESOURCE_ATTRIBUTES="gcp.project_id=your-project-id,service.name=my-service"
```

---

## Migrate from OpenTelemetry Google Cloud Trace Exporter (`CloudTraceSpanExporter`) to OTLP Exporter

To migrate from `opentelemetry-exporter-gcp-trace` (`CloudTraceSpanExporter`) to the standard OpenTelemetry OTLP exporter, follow these steps:

### 1. Add Dependencies

Install the standard OpenTelemetry OTLP exporter, GCP resource detector, and GCP authentication dependencies:

```bash
pip install opentelemetry-exporter-otlp-proto-grpc opentelemetry-resourcedetector-gcp google-auth grpcio requests
```

### 2. Configure the SDK

You can configure the SDK using environment variables:

```bash
# Environment Variables
export OTEL_EXPORTER_OTLP_ENDPOINT="https://telemetry.googleapis.com"
export OTEL_TRACES_EXPORTER="otlp"
export OTEL_EXPORTER_OTLP_PROTOCOL="http/protobuf"
export OTEL_EXPERIMENTAL_RESOURCE_DETECTORS="gcp"
```

Or programmatically in Python using GCP authentication:

```python
import google.auth
import google.auth.transport.grpc
import google.auth.transport.requests
import grpc
from google.auth.transport.grpc import AuthMetadataPlugin
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Configure GCP Authentication
credentials, project_id = google.auth.default()
request = google.auth.transport.requests.Request()
auth_metadata_plugin = AuthMetadataPlugin(
    credentials=credentials, request=request
)
channel_creds = grpc.composite_channel_credentials(
    grpc.ssl_channel_credentials(),
    grpc.metadata_call_credentials(auth_metadata_plugin),
)

trace.set_tracer_provider(TracerProvider())

otlp_exporter = OTLPSpanExporter(
    endpoint="telemetry.googleapis.com",
    credentials=channel_creds,
)
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(otlp_exporter)
)
```

### 3. Follow the Migration Guide

For more details, follow the official Google Cloud guide: [Migrate from the Trace exporter to the OTLP endpoint](https://docs.cloud.google.com/trace/docs/migrate-to-otlp-endpoints).

### Mapping and Limitations

#### Configuration Mapping

| `CloudTraceSpanExporter` Parameter | OTLP Equivalent Property / Env Var | Notes |
| :--- | :--- | :--- |
| `project_id` / `OTEL_EXPORTER_GCP_TRACE_PROJECT_ID` | Resource attribute: `gcp.project_id` | Set via `OTEL_RESOURCE_ATTRIBUTES="gcp.project_id=your-project-id"` or detected automatically via `opentelemetry-resourcedetector-gcp`. |
| `client` | N/A | Pre-configured `TraceServiceClient` is replaced by OTLP gRPC/HTTP channel credentials. |
| `resource_regex` | Standard Resource Attributes | Standard OpenTelemetry exports resource attributes attached to the `TracerProvider`. Filtering/copying resource attributes via regex is not supported in OTLP. |

#### Unsupported Features

* **Attribute Mapping & Regex Filtering (`resource_regex`)**: `CloudTraceSpanExporter` allowed filtering resource attributes via regex to copy matching keys into span attributes. The standard OTLP exporter exports standard OpenTelemetry resource attributes attached to the `TracerProvider` directly.
* **Custom Trace Service Client (`client`)**: You cannot pass a pre-configured `TraceServiceClient` instance directly to `OTLPSpanExporter`. If custom gRPC channels or metadata credentials are required, configure gRPC channel credentials programmatically as shown above.

#### Data Model differences & Data Limit Improvements

Cloud Trace’s internal storage system uses the OpenTelemetry data model natively for organizing and storing your trace data. For complete documentation on OTLP trace mapping and limits, see [Migrate from the Trace exporter to the OTLP endpoint](https://cloud.google.com/trace/docs/migrate-to-otlp-endpoints).


##### Data Model Comparison

* **Payload Hierarchy & Resource Model:**
  - **`CloudTraceSpanExporter` (API v2):** Sent a flat list of `Span` objects (`BatchWriteSpansRequest`). Because Cloud Trace v2 spans had no native resource container, resource attributes were flattened on the client side into span labels prefixed with `g.co/r/<resource_type>/<label_key>`.
  - **OTLP Exporter (Native OTel Storage Model):** Uses the structured OTLP hierarchy (`ExportTraceServiceRequest` → `ResourceSpans` → `ScopeSpans` → `Span`). Resource attributes (`gcp.project_id`, `host.id`, `k8s.pod.name`, etc.) are stored natively in the `ResourceSpans` envelope and mapped server-side.
* **Attribute Keys & Semantic Conventions:**
  - **`CloudTraceSpanExporter`:** Performed client-side remapping of OpenTelemetry HTTP keys to legacy Cloud Trace `/http/` label keys (e.g., `http.method` → `/http/method`, `http.status_code` → `/http/status_code`).
  - **OTLP Exporter:** Preserves standard OpenTelemetry semantic convention keys (e.g., `http.request.method`, `http.response.status_code`, `url.full`) verbatim, stored and indexed natively in Cloud Trace.

##### Expanded Limits Comparison

For complete documentation on OTLP trace mapping and limits, see [Migrate from the Trace exporter to the OTLP endpoint](https://cloud.google.com/trace/docs/migrate-to-otlp-endpoints).

## Migrate from OpenTelemetry Google Cloud Monitoring Exporter (`CloudMonitoringMetricsExporter`) to OTLP Exporter

> [!WARNING]
> **Breaking Change Warning:** Migrating from the legacy Google Cloud Monitoring exporter to the standard OTLP exporter introduces breaking changes to your metric names.
>
> * **Legacy Exporter:** Ingests metrics under the `workload.googleapis.com/` domain (unless a custom prefix was configured).
> * **OTLP Exporter:** Ingests metrics under the `prometheus.googleapis.com/` domain by default.
>
> Because of this domain change, your metric names in Cloud Monitoring will change. **This will break any existing dashboards, alerting policies, and cause data discontinuity** between your historical and new metrics.

### Why Migrate?

While this migration introduces breaking changes, transitioning to the standard OTLP exporter is recommended for the following reasons:
* **Standardization:** Aligns your application with the industry-standard OpenTelemetry Protocol (OTLP), ensuring vendor neutrality and compatibility with the broader OpenTelemetry ecosystem.
* **Google Managed Prometheus (GMP) Cost Savings:** Standard OTLP metrics are ingested into Google Managed Prometheus. GMP offers a robust, scalable, and cost-effective monitoring solution (~20x cheaper ingestion cost than legacy Cloud Monitoring API ingestion).
* **Future-proofing:** The legacy Google Cloud Monitoring exporter is deprecated. Migrating now ensures your monitoring pipeline remains supported.

---

### Migration Strategies

We recommend three paths for migration, depending on your operational requirements:

1. **Direct Migration (Recommended):** Migrate fully to the OTLP exporter and update your dashboards and alerts to use the new metric names under the `prometheus.googleapis.com/` domain.
2. **Transition via Double-Writing (Alternative):** Run both the legacy exporter and the OTLP exporter in parallel. This allows you to validate the new OTLP pipeline and update dashboards/alerts without any monitoring downtime, at the cost of temporary double-ingestion charges.
3. **Custom Metric Renaming / View Configuration (Alternative):** Use OpenTelemetry SDK Views or metric processors (or OpenTelemetry Collector relabeling) to map metric names and attributes, allowing you to maintain compatibility with existing dashboards.

---

### Strategy 1: Direct Migration (Recommended)

Follow these steps to fully transition to the standard OTLP exporter.

#### 1. Add Dependencies

```bash
pip install opentelemetry-exporter-otlp-proto-grpc opentelemetry-resourcedetector-gcp google-auth grpcio
```

#### 2. Configure Environment Variables

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="https://telemetry.googleapis.com"
export OTEL_METRICS_EXPORTER="otlp"
export OTEL_EXPORTER_OTLP_PROTOCOL="http/protobuf"
export OTEL_EXPERIMENTAL_RESOURCE_DETECTORS="gcp"
export OTEL_RESOURCE_ATTRIBUTES="gcp.project_id=$PROJECT_ID,location=us-central1,service.name=otlp-sample,service.instance.id=1"
```

#### 3. Programmatic Configuration

```python
import google.auth
import google.auth.transport.grpc
import google.auth.transport.requests
import grpc
from google.auth.transport.grpc import AuthMetadataPlugin
from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
    OTLPMetricExporter,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

# Configure GCP Authentication
credentials, project_id = google.auth.default()
request = google.auth.transport.requests.Request()
auth_metadata_plugin = AuthMetadataPlugin(
    credentials=credentials, request=request
)
channel_creds = grpc.composite_channel_credentials(
    grpc.ssl_channel_credentials(),
    grpc.metadata_call_credentials(auth_metadata_plugin),
)

exporter = OTLPMetricExporter(
    endpoint="telemetry.googleapis.com",
    credentials=channel_creds,
)
reader = PeriodicExportingMetricReader(exporter)
provider = MeterProvider(metric_readers=[reader])
metrics.set_meter_provider(provider)
```

### Strategy 2: Transition via Double-Writing

To avoid monitoring gaps, run both the legacy exporter (`CloudMonitoringMetricsExporter`) and the standard OTLP exporter (`OTLPMetricExporter`) concurrently. This sends metrics to both `workload.googleapis.com/` and `prometheus.googleapis.com/` simultaneously, allowing you to update dashboards and alerting policies without any monitoring downtime.

> [!NOTE]
> **Cost Consideration:**  Double-writing metrics will double your metric ingestion volume, which will increase your Google Cloud Monitoring costs during the transition period. It also increases CPU and memory usage on your application.

```python
import google.auth
import google.auth.transport.grpc
import google.auth.transport.requests
import grpc
from google.auth.transport.grpc import AuthMetadataPlugin
from opentelemetry import metrics
from opentelemetry.exporter.cloud_monitoring import (
    CloudMonitoringMetricsExporter,
)
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
    OTLPMetricExporter,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

credentials, project_id = google.auth.default()
request = google.auth.transport.requests.Request()
auth_metadata_plugin = AuthMetadataPlugin(
    credentials=credentials, request=request
)
channel_creds = grpc.composite_channel_credentials(
    grpc.ssl_channel_credentials(),
    grpc.metadata_call_credentials(auth_metadata_plugin),
)

# 1. Instantiate legacy exporter (writes to workload.googleapis.com/)
legacy_exporter = CloudMonitoringMetricsExporter(project_id=project_id)

# 2. Instantiate OTLP exporter (writes to prometheus.googleapis.com/)
otlp_exporter = OTLPMetricExporter(
    endpoint="telemetry.googleapis.com",
    credentials=channel_creds,
)

# 3. Register both readers with MeterProvider
provider = MeterProvider(
    metric_readers=[
        PeriodicExportingMetricReader(legacy_exporter),
        PeriodicExportingMetricReader(otlp_exporter),
    ]
)
metrics.set_meter_provider(provider)
```

#### Verification and Cutover

1. **Verify New Metrics Ingestion:** Once double-writing is deployed, verify in Metrics Explorer that new metrics are arriving under the `prometheus.googleapis.com/` domain.
2. **Update Dashboards & Alerts:** Duplicate or update existing Cloud Monitoring dashboards, charts, and alerting policies to query `prometheus.googleapis.com/` metric names instead of `workload.googleapis.com/`.
3. **Cutover & Decommission:** Once all dashboards and alerting rules are updated and verified against the new OTLP metric data streams, remove `CloudMonitoringMetricsExporter` from your `MeterProvider` to complete the migration and eliminate double-ingestion.

### Strategy 3: Custom Metric Prefixing / Wrapped Exporter

If you want to preserve legacy metric prefixes (such as `workload.googleapis.com/`) during migration, wrap your `MetricExporter` with a custom exporter wrapper that prepends the prefix to metric names before export.

```python
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    MetricExporter,
    MetricExportResult,
    MetricsData,
    ResourceMetrics,
    ScopeMetrics,
    Metric,
    PeriodicExportingMetricReader,
)


class PrefixMetricExporter(MetricExporter):
    """Wraps a MetricExporter to prepend a prefix to metric names before export."""

    def __init__(
        self,
        delegate: MetricExporter,
        prefix: str = "workload.googleapis.com/",
    ):
        super().__init__(
            preferred_temporality=getattr(delegate, "_preferred_temporality", None),
            preferred_aggregation=getattr(delegate, "_preferred_aggregation", None),
        )
        self._delegate = delegate
        self._prefix = prefix

    def export(
        self,
        metrics_data: MetricsData,
        timeout_millis: float = 10_000,
        **kwargs,
    ) -> MetricExportResult:
        new_resource_metrics = []
        for rm in metrics_data.resource_metrics:
            new_scope_metrics = []
            for sm in rm.scope_metrics:
                new_metrics = []
                for m in sm.metrics:
                    new_metrics.append(
                        Metric(
                            name=f"{self._prefix}{m.name}",
                            description=m.description,
                            unit=m.unit,
                            data=m.data,
                        )
                    )
                new_scope_metrics.append(
                    ScopeMetrics(
                        scope=sm.scope,
                        metrics=new_metrics,
                        schema_url=sm.schema_url,
                    )
                )
            new_resource_metrics.append(
                ResourceMetrics(
                    resource=rm.resource,
                    scope_metrics=new_scope_metrics,
                    schema_url=rm.schema_url,
                )
            )
        new_metrics_data = MetricsData(resource_metrics=new_resource_metrics)
        return self._delegate.export(
            new_metrics_data, timeout_millis=timeout_millis, **kwargs
        )

    def shutdown(self, timeout_millis: float = 30_000, **kwargs) -> None:
        self._delegate.shutdown(timeout_millis=timeout_millis, **kwargs)

    def force_flush(self, timeout_millis: float = 10_000, **kwargs) -> bool:
        return self._delegate.force_flush(timeout_millis=timeout_millis, **kwargs)


# Wrap the OTLPMetricExporter with the prefix exporter
exporter = PrefixMetricExporter(
    delegate=otlp_exporter,
    prefix="workload.googleapis.com/",
)

provider = MeterProvider(
    metric_readers=[PeriodicExportingMetricReader(exporter)],
)
metrics.set_meter_provider(provider)
```


### Mapping and Limitations

#### Configuration Mapping

| `CloudMonitoringMetricsExporter` Parameter | OTLP Equivalent Property / Env Var | Notes |
| :--- | :--- | :--- |
| `prefix` (default `workload.googleapis.com`) | N/A | Legacy exporter ingested under `workload.googleapis.com/` (or custom prefix). OTLP exporter ingests into Google Managed Prometheus under `prometheus.googleapis.com/` by default. |
| `add_unique_identifier` | Resource Attributes (e.g. `service.instance.id`, `host.id`) | Legacy exporter appended a random identifier to time series. OTLP relies on standard OpenTelemetry resource attributes to distinguish instances. |
| `project_id` | Resource attribute: `gcp.project_id` | Set via `OTEL_RESOURCE_ATTRIBUTES="gcp.project_id=your-project-id"` or detected automatically via `opentelemetry-resourcedetector-gcp`. |
| `client` | N/A | Pre-configured `MetricServiceClient` cannot be passed directly to `OTLPMetricExporter`. |

#### Conversion Logic & Metric Mapping Differences

The conversion logic used in `CloudMonitoringMetricsExporter` can be found in [`opentelemetry-exporter-gcp-monitoring/src/opentelemetry/exporter/cloud_monitoring/__init__.py`](opentelemetry-exporter-gcp-monitoring/src/opentelemetry/exporter/cloud_monitoring/__init__.py#L184-L365). Standard OTLP endpoints convert OTLP metric data server-side according to the [Google Cloud Telemetry API Metric Mapping specification](https://docs.cloud.google.com/stackdriver/docs/reference/telemetry/v1.metrics#metric-mapping-reference-info).

Key differences include:

* **Metric Domain & Name Structure:**
  - **`CloudMonitoringMetricsExporter`:** Ingests metrics under `workload.googleapis.com/<metric.name>` (or custom `prefix`).
  - **Telemetry API:** Ingests metrics under `prometheus.googleapis.com/<metric_name>/<suffix>` (e.g. `/counter`, `/gauge`, `/histogram`, `/delta`, `/summary`). You can override the prefix to `workload.googleapis.com/` or `custom.google.com/` using the strategies mentioned above, but no other prefix is accepted by the API.
* **Value Types (`INT64` vs `DOUBLE`):**
  - **`CloudMonitoringMetricsExporter`:** Preserves `INT64` value types when integer data points are passed (`TypedValue(int64_value=...)`).
  - **Telemetry API:** Translates **all OTLP `INT64` scalar metrics to `DOUBLE`** in Cloud Monitoring to prevent Monarch value-type schema collisions.
* **Metric Kind & Temporality:**
  - Monotonic cumulative sums map to `CUMULATIVE` (suffixed with `/counter`).
  - Monotonic delta sums map to `DELTA` (suffixed with `/delta`).
  - Non-monotonic sums map to `GAUGE` (suffixed with `/gauge`). Non-monotonic delta sums are not supported.
  - Histograms support both `CUMULATIVE` (`/histogram`) and `DELTA` (`/histogram:delta`) distributions.
  - Summary metrics are expanded into individual time series for `_count` (`CUMULATIVE`), `_sum` (`CUMULATIVE`), and `quantile` (`GAUGE` with a `quantile` label).
* **Resource Attributes & `target_info` Metric:**
  - **`CloudMonitoringMetricsExporter`:** Maps OpenTelemetry resources to GCP `MonitoredResource` on the client side using `get_monitored_resource()`. Optionally appends a random `opentelemetry_id` label when `add_unique_identifier=True`.
  - **Telemetry API:** Maps resources server-side and automatically generates a `target_info` metric for each unique OpenTelemetry resource containing non-identifying resource attributes.
* **Special Characters:** The Telemetry API preserves `.` and `/` characters in OTLP metric names rather than replacing them with underscores (`_`).

---

## Migrate from OpenTelemetry Google Cloud Logging Exporter (`CloudLoggingExporter`) to OTLP Exporter

The OTLP `LogRecord` to Cloud Logging `LogEntry` conversion logic in standard OTLP endpoints is described in the [Google OTLP LogRecord to LogEntry specification](https://docs.cloud.google.com/stackdriver/docs/reference/telemetry/otlp-log-record-to-log-entry). The conversion logic used in `CloudLoggingExporter` can be found in [`opentelemetry-exporter-gcp-logging/src/opentelemetry/exporter/cloud_logging/__init__.py`](opentelemetry-exporter-gcp-logging/src/opentelemetry/exporter/cloud_logging/__init__.py#L331-L380) and is different in some ways, you should not expect
the format of the log to look exactly the same after switching over. 

To migrate from `opentelemetry-exporter-gcp-logging` (`CloudLoggingExporter`) to the standard OpenTelemetry OTLP log exporter, follow these steps:

### 1. Add Dependencies

Install the standard OpenTelemetry OTLP log exporter package and GCP resource detector:

```bash
pip install opentelemetry-exporter-otlp-proto-grpc opentelemetry-resourcedetector-gcp google-auth grpcio
```

### 2. Configure Environment Variables

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="https://telemetry.googleapis.com"
export OTEL_LOGS_EXPORTER="otlp"
export OTEL_EXPORTER_OTLP_PROTOCOL="http/protobuf"
export OTEL_EXPERIMENTAL_RESOURCE_DETECTORS="gcp"
export OTEL_RESOURCE_ATTRIBUTES="gcp.project_id=$PROJECT_ID,service.name=otlp-sample,service.instance.id=1"
```

### 3. Programmatic Configuration

```python
import logging
import google.auth
import google.auth.transport.grpc
import google.auth.transport.requests
import grpc
from google.auth.transport.grpc import AuthMetadataPlugin
from opentelemetry import _logs
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import (
    OTLPLogExporter,
)
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor

# Configure GCP Authentication
credentials, project_id = google.auth.default()
request = google.auth.transport.requests.Request()
auth_metadata_plugin = AuthMetadataPlugin(
    credentials=credentials, request=request
)
channel_creds = grpc.composite_channel_credentials(
    grpc.ssl_channel_credentials(),
    grpc.metadata_call_credentials(auth_metadata_plugin),
)

logger_provider = LoggerProvider()
_logs.set_logger_provider(logger_provider)

otlp_log_exporter = OTLPLogExporter(
    endpoint="telemetry.googleapis.com",
    credentials=channel_creds,
)
logger_provider.add_log_record_processor(
    BatchLogRecordProcessor(otlp_log_exporter)
)
```

### Mapping and Limitations

#### Conversion Logic & Log Entry Mapping

* **Log Entry Conversion:** The conversion logic in `CloudLoggingExporter` can be found in [`opentelemetry-exporter-gcp-logging/src/opentelemetry/exporter/cloud_logging/__init__.py`](opentelemetry-exporter-gcp-logging/src/opentelemetry/exporter/cloud_logging/__init__.py#L331-L380). Standard OTLP endpoints convert OTLP `LogRecord` payloads server-side according to the [OTLP LogRecord to LogEntry specification](https://docs.cloud.google.com/stackdriver/docs/reference/telemetry/otlp-log-record-to-log-entry).
* **Log Names & Resources:** The OTLP endpoint maps log names from resource attributes (e.g. `gcp.log_name` or defaults to `projects/<project>/logs/otel`).
* **Query Impact:** If your existing Cloud Logging log queries filter by specific `logName` values (such as python logger names mapped by `CloudLoggingExporter`), you may need to update your Cloud Logging query filters to match the OTLP log names and attributes.
* **GCP Monitored Resource Association:** Installing `opentelemetry-resourcedetector-gcp` ensures log records contain appropriate GCP resource attributes, allowing Cloud Logging to associate logs with standard monitored resources (GCE instances, GKE pods, Cloud Run services, etc.).

---

## Migrate from X-Cloud-Trace-Context Propagator to W3C Trace Context Propagator

Google Cloud infrastructure now natively supports standard W3C Trace Context headers (`traceparent` and `tracestate`). The `opentelemetry-propagator-gcp` package is deprecated and will be archived after October 30th, 2026. You should migrate to standard OpenTelemetry W3C Trace Context propagation.

### Why Migrate?

* **Standardization:** W3C Trace Context is the industry standard for distributed tracing context propagation and is natively supported across cloud providers, libraries, and frameworks.
* **Native GCP Support:** Google Cloud services (such as Cloud Run, Cloud Functions, App Engine, Google Kubernetes Engine, Cloud Trace, and Google Cloud Load Balancers) natively support W3C Trace Context headers without requiring proprietary headers.
* **Built-in OpenTelemetry Support:** W3C Trace Context propagation is built into the core `opentelemetry-api` package and is enabled by default in OpenTelemetry Python.

---

### Migration Steps

#### 1. Remove Legacy Dependency

Remove the `opentelemetry-propagator-gcp` dependency from your project (`requirements.txt`, `pyproject.toml`, etc.):

```bash
pip uninstall opentelemetry-propagator-gcp
```

The standard W3C Trace Context propagator is included automatically with `opentelemetry-api`.

#### 2. Update Configuration (Auto-Instrumentation / CLI)

When using OpenTelemetry auto-instrumentation (`opentelemetry-instrument`), W3C Trace Context (`tracecontext`) and Baggage (`baggage`) are used by default (`OTEL_PROPAGATORS="tracecontext,baggage"`).

If you explicitly configured `OTEL_PROPAGATORS` to include `gcp_trace`, update it to remove it:

```bash
# Environment Variables
OTEL_PROPAGATORS="tracecontext,baggage"
```

If you use the `opentelemetry-instrument` CLI for auto-instrumentation, remove the `--propagator gcp_trace` flag:

```bash
# Before
opentelemetry-instrument --propagator gcp_trace python main.py

# After (uses default W3C Trace Context and Baggage propagators)
opentelemetry-instrument python main.py
```

#### 3. Update Manual Configuration in Code

If you manually registered `CloudTraceFormatPropagator` in your application code, replace it with the standard OpenTelemetry `TraceContextTextMapPropagator` (and optionally `W3CBaggagePropagator`):

##### Before (Legacy GCP Propagator)

```python
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.cloud_trace_propagator import (
    CloudTraceFormatPropagator,
)

# Sets the X-Cloud-Trace-Context header propagator
set_global_textmap(CloudTraceFormatPropagator())
```

##### After (Standard W3C Trace Context Propagator)

```python
from opentelemetry.baggage.propagation import W3CBaggagePropagator
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.composite import CompositePropagator
from opentelemetry.trace.propagation.tracecontext import (
    TraceContextTextMapPropagator,
)

# Set standard W3C Trace Context and Baggage propagators
set_global_textmap(
    CompositePropagator([
        TraceContextTextMapPropagator(),
        W3CBaggagePropagator(),
    ])
)
```

> [!NOTE]
> When using `opentelemetry-instrument` (or relying on default `opentelemetry-api` propagation), standard W3C propagation is enabled automatically by default without requiring manual code setup.
