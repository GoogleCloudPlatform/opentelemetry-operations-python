"""Provides a mechanism to configure the Metrics Exporter for GCP."""
from opentelemetry import metrics as otel_metrics
from opentelemetry.sdk import metrics as otel_metrics_sdk
from opentelemetry.sdk.metrics import export as otel_metrics_sdk_export
from opentelemetry.exporter import cloud_monitoring as otel_cloud_monitoring


def configure_metrics_exporter(resource=None):
    """Configures the Open Telemetry metrics library to write to Cloud Monitoring.
    
    Args:
      resource: The resource to use when writing metrics.

    Effects:
      Calls 'set_meter_provider' with a MeterProvider that will cause
      Open Telemetry metrics to get routed to Cloud Monitoring.
    """
    provider = otel_metrics_sdk.MeterProvider(
        metric_readers=[
            otel_metrics_sdk_export.PeriodicExportingMetricReader(
                otel_cloud_monitoring.CloudMonitoringMetricsExporter()
            ),
        ],
        resource=resource)
    otel_metrics.set_meter_provider(provider)
