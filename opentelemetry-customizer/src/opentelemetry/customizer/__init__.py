from opentelemetry.sdk._config_customizer import _BaseConfiguratorCustomizer
import inspect
from opentelemetry.sdk._logs.export import LogExporter
from opentelemetry.sdk.metrics.export import (
    MetricExporter,
)
from typing import Type, Union
from opentelemetry.sdk.trace.export import SpanExporter
import google.auth
import grpc
from google.auth.transport import requests as auth_requests
from google.auth.transport.grpc import AuthMetadataPlugin
from google.auth.transport.requests import AuthorizedSession
from opentelemetry.resourcedetector.gcp_resource_detector._detector import (
    GoogleCloudResourceDetector,
)


class GoogleCloudConfiguratorCustomizer(_BaseConfiguratorCustomizer):
    def __init__(
        self,
        send_metrics_to_gcp: bool = False,
        send_logs_to_gcp: bool = False,
        send_spans_to_gcp: bool = False,
    ):
        self.send_metrics_to_gcp = send_metrics_to_gcp
        self.send_logs_to_gcp = send_logs_to_gcp
        self.send_spans_to_gcp = send_spans_to_gcp
        credentials, _ = google.auth.default()
        self.channel_credentials = grpc.composite_channel_credentials(
            grpc.ssl_channel_credentials(),
            grpc.metadata_call_credentials(
                AuthMetadataPlugin(
                    credentials=credentials, request=auth_requests.Request()
                )
            ),
        )
        self.session = AuthorizedSession(credentials)

    def init_resource(self):
        return GoogleCloudResourceDetector().detect()

    def init_log_exporter(self, log_exporter: Type[LogExporter]) -> LogExporter:
        return self._init_exporter(self.send_logs_to_gcp, log_exporter)

    def init_metric_exporter(
        self,
        metric_exporter: Type[MetricExporter],
    ) -> MetricExporter:
        return self._init_exporter(self.send_metrics_to_gcp, metric_exporter)

    def init_span_exporter(
        self,
        span_exporter: Type[SpanExporter],
    ) -> SpanExporter:
        return self._init_exporter(self.send_spans_to_gcp, span_exporter)

    def _init_exporter(
        self,
        customize_exporter: bool,
        exporter_class: Type[Union[SpanExporter, MetricExporter, LogExporter]],
    ) -> Union[SpanExporter, MetricExporter, LogExporter]:
        if not customize_exporter:
            print("initializing class")
            return exporter_class()
        params = inspect.signature(exporter_class.__init__).parameters
        if "credentials" in params and "grpc.ChannelCredentials" in str(
            params["credentials"].annotation
        ):
            return exporter_class(
                credentials=self.channel_credentials,
                endpoint="telemetry.googleapis.com",
            )
        if "session" in params and str(
            "requests.Session" in params["session"].annotation
        ):
            return exporter_class(
                session=self.session, endpoint="telemetry.googleapis.com"
            )
        return exporter_class()


def send_metrics_and_traces_to_gcp() -> GoogleCloudConfiguratorCustomizer:
    return GoogleCloudConfiguratorCustomizer(
        send_spans_to_gcp=True, send_metrics_to_gcp=True
    )


def send_logs_and_traces_to_gcp() -> GoogleCloudConfiguratorCustomizer:
    return GoogleCloudConfiguratorCustomizer(
        send_logs_to_gcp=True, send_spans_to_gcp=True
    )


def send_logs_and_metrics_to_gcp() -> GoogleCloudConfiguratorCustomizer:
    return GoogleCloudConfiguratorCustomizer(
        send_logs_to_gcp=True, send_metrics_to_gcp=True
    )


def send_only_traces_to_gcp() -> GoogleCloudConfiguratorCustomizer:
    return GoogleCloudConfiguratorCustomizer(
        send_spans_to_gcp=True,
    )


def send_only_metrics_to_gcp() -> GoogleCloudConfiguratorCustomizer:
    return GoogleCloudConfiguratorCustomizer(
        send_metrics_to_gcp=True,
    )


def send_only_logs_to_gcp() -> GoogleCloudConfiguratorCustomizer:
    return GoogleCloudConfiguratorCustomizer(
        send_logs_to_gcp=True,
    )


def send_all_telemetry_to_gcp() -> GoogleCloudConfiguratorCustomizer:
    return GoogleCloudConfiguratorCustomizer(
        send_spans_to_gcp=True,
        send_metrics_to_gcp=True,
        send_logs_to_gcp=True,
    )
