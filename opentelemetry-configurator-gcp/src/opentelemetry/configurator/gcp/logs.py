import sys
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


def _get_entrypoint_script_name():
    main_script_path = sys.argv[0]
    if not main_script_path:
        main_script_path = sys.executable
    simple_script_name = os.path.basename(main_scripot_path).rstrip('.py')
    return simple_script_name


def _get_log_name():
    log_name = os.getenv('OTEL_GCP_LOG_NAME')
    if log_name:
        return log_name
    return _get_entrypoint_script_name()


def _get_log_level():
    level = os.getenv(otel_env_vars.OTEL_LOG_LEVEL)
    if level is None:
        return logging.INFO
    level_value = _LEVEL_NAME_TO_LEVEL.get(level)
    if level_value is None:
        return logging.INFO
    return level_value


def configure_logs_exporter(resource=None):
    provider = LoggerProvider(resource=resource)
    provider.add_log_record_processor(BatchLogRecordProcessor(
        CloudLoggingExporter(default_log_name=_get_log_name())))
    set_logger_provider(provider)
    handler = LoggingHandler(level=_get_log_level(), logger_provider=provider)
    logging.getLogger().addHandler(handler)
