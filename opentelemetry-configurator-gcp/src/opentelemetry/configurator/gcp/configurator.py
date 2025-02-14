from typing import Optional, Callable

from .flags import (
    is_metrics_exporter_enabled,
    is_logs_exporter_enabled,
    is_traces_exporter_enabled,
    is_resource_detector_enabled,
)
from .resource import get_resource
from .logs import configure_logs_exporter
from .metrics import configure_metrics_exporter
from .traces import configure_traces_exporter


def _bool_with_flag_default(value: Optional[bool], flag_lookup: Callable[None, bool]):
    if value is not None:
        return value
    return flag_lookup()


class OpenTelemetryGcpConfigurator:

    def __init__(
        self,
        metrics_exporter_enabled:Optional[bool]=None,
        logs_exporter_enabled:Optional[bool]=None,
        traces_exporter_enabled:Optional[bool]=None,
        resource_detector_enabled:Optional[bool]=None):
        self._metrics_exporter_enabled = _bool_with_flag_default(
            metrics_exporter_enabled, is_metrics_exporter_enabled)
        self._logs_exporter_enabled = _bool_with_flag_default(
            logs_exporter_enabled, is_logs_exporter_enabled)
        self._traces_exporter_enabled = _bool_with_flag_default(
            traces_exporter_enabled, is_traces_exporter_enabled)
        self._resource_detector_enabled = _bool_with_flag_default(
            resource_detector_enabled, is_resource_detector_enabled)

    def configure(self):
        resource = get_resource(include_gcp_detector=self._resource_detector_enabled)
        if self._metrics_exporter_enabled:
            configure_metrics_exporter(resource=resource)
        if self._logs_exporter_enabled:
            configure_logs_exporter(resource=resource)
        if self._traces_exporter_enabled:
            configure_traces_exporter(resource=resource)

