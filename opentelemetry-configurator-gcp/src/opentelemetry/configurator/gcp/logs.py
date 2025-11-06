"""Provides a mechanism to configure the Logs Exporter for GCP."""
import os
import os.path
import logging
from opentelemetry.exporter.cloud_logging import (
    CloudLoggingExporter,
)
from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk import environment_variables as otel_env_vars
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor


_LEVEL_NAME_TO_LEVEL = {
    'info': logging.INFO,
    'error': logging.ERROR,
    'debug': logging.DEBUG,
    'warning': logging.WARNING,
}


def _get_log_level():
    level = os.getenv(otel_env_vars.OTEL_LOG_LEVEL)
    if level is None:
        return logging.INFO
    level_value = _LEVEL_NAME_TO_LEVEL.get(level)
    if level_value is None:
        return logging.INFO
    return level_value


def configure_logs_exporter(resource=None):
    """Configures the Cloud Logging exporter.
    
    Args:
        resource: the resource to include in the emitted logs

    Effects:
        - Invokes the 'set_logger_provider' function with an
          exporter that will cause OTel logs to get routed to GCP.
        - Modifies the built-in 'logging' component in Python to
          route built-in Python logs to Open Telemetry.
    """
    provider = LoggerProvider(resource=resource)
    provider.add_log_record_processor(BatchLogRecordProcessor(CloudLoggingExporter()))
    set_logger_provider(provider)
    handler = LoggingHandler(level=_get_log_level(), logger_provider=provider)
    logging.getLogger().addHandler(handler)
