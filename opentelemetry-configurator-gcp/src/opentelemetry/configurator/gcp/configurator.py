"""Defines the 'OpenTelemetryGcpConfigurator' class for simplifying Open Telemetry setup for GCP."""
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


class OpenTelemetryGcpConfigurator:  # pylint: disable=too-few-public-methods
    """A class that can be used as a configurator in Open Telemetry zero-code instrumentation."""

    def __init__(
        self,
        metrics_exporter_enabled:Optional[bool]=None,
        logs_exporter_enabled:Optional[bool]=None,
        traces_exporter_enabled:Optional[bool]=None,
        resource_detector_enabled:Optional[bool]=None):
        """Initialize the configurator with optional parameters to direct the behavior.
        
        No arguments are supplied when invoked from the zero-configuration system.

        Args:
          metrics_exporter_enabled: whether to enable metrics export. If unset,
            falls back to an environment variable, allowing this argument to
            be supplied even in zero-configuration scenarios. If that, too,
            is unset, then the metrics export will be enabled.

          logs_exporter_enabled: whether to enable logs export. If unset,
            falls back to an environment variable, allowing this argument to
            be supplied even in zero-configuration scenarios. If that, too,
            is unset, then the logs export will be enabled.

          traces_exporter_enabled: whether to enable trace export. If unset,
            falls back to an environment variable, allowing this argument to
            be supplied even in zero-configuration scenarios. If that, too,
            is unset, then the trace export will be enabled.

          resource_detector_enabled: whether to enable the GCP resource
            detector (which is useful only when the code is running in
            a GCP environment). If unset, falls back to an environment variable,
            allowing this argument to be supplied even in zero-configuration
            scenarios. If that, too, is unset, then the code will attempt
            to determine if the code is likely deployed in GCP or not
            based on the environment to enable the detector or not.
        
        Environment Variables:

           The following environment variables affect the defaults:

             - OTEL_GCP_METRICS_EXPORTER_ENABLED
             - OTEL_GCP_LOGS_EXPORTER_ENABLED
             - OTEL_GCP_TRACES_EXPORTER_ENABLED
             - OTEL_GCP_RESOURCE_DETECTOR_ENABLED
        """
        self._metrics_exporter_enabled = _bool_with_flag_default(
            metrics_exporter_enabled, is_metrics_exporter_enabled)
        self._logs_exporter_enabled = _bool_with_flag_default(
            logs_exporter_enabled, is_logs_exporter_enabled)
        self._traces_exporter_enabled = _bool_with_flag_default(
            traces_exporter_enabled, is_traces_exporter_enabled)
        self._resource_detector_enabled = _bool_with_flag_default(
            resource_detector_enabled, is_resource_detector_enabled)

    def configure(self, **unused_kwargs):
        """Configure the Open Telemetry library to talk to GCP backends.
        
        This function configures the Open Telemetry library to talk to GCP
        backends, subject to the class initialization parameters.

        Although this class does not inherit any explicit interface, this
        function should be treated like an inherited method in that its
        signature is dictated by the Open Telemetry auto-instrumentation.

        Uses **unused_kwargs to allow future iterations of the Open Telemetry
        library to introduce additional keyword arguments without breaking.
        """
        resource = get_resource(include_gcp_detector=self._resource_detector_enabled)
        if self._metrics_exporter_enabled:
            configure_metrics_exporter(resource=resource)
        if self._logs_exporter_enabled:
            configure_logs_exporter(resource=resource)
        if self._traces_exporter_enabled:
            configure_traces_exporter(resource=resource)
