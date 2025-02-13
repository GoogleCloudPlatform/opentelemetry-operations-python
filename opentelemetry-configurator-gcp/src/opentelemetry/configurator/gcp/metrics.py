from opentelemetry import metrics as otel_metrics
from opentelemetry.sdk import metrics as otel_metrics_sdk
from opentelemetry.sdk.metrics import export as otel_metrics_sdk_export
from opentelemetry.exporter import cloud_monitoring as otel_cloud_monitoring


def configure_metrics_exporter(resource=None):
    provider = otel_metrics_sdk.MeterProvider(
        metric_readers=[
            otel_metrics_sdk_export.PeriodicExportingMetricReader(
                otel_cloud_monitoring.CloudMonitoringMetricsExporter()
            ),
        ],
        resource=resource)
    otel_metrics.set_meter_provider(provider)
