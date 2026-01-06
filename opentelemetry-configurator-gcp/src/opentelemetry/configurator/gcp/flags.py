"""Provides functions for querying the configuration of this library.

Other modules in this package use the 'flags' library to obtain default
behaviors where the behavior has not been explicitly specified.
"""
from typing import Optional

import os

from . import gcloud_env


def _str_to_optional_bool(s: str) -> Optional[bool]:
    """Converts a string to an optional boolean.
    
    Args:
        s: the string to convert to a boolean

    Returns:
        A boolean if the value is clearly false or clearly true.
        None if the string does not match a known true/false pattern.
    """
    lower_s = s.lower()
    if lower_s in ['1', 'true', 't', 'y', 'yes', 'on']:
        return True
    if lower_s in ['0', 'false', 'f', 'n', 'no', 'off']:
        return False
    return None


def _get_bool_flag_from_env(env_var_name: str, default_value:Optional[bool]=None) -> Optional[bool]:
    """Retrieves a boolean value from an environment variable.
    
    Args:
      env_var_name: The name of the environment variable to retrieve.
      default_value: The value to return if unset or has a non-bool value.
    
    Returns:
      The boolean value of the environment variable if set and valid.
      Otherwise, falls back to the supplied default value.
    """
    s = os.getenv(env_var_name)
    if s is None:
        return default_value
    result = _str_to_optional_bool(s)
    if result is not None:
        return result
    return default_value


def is_metrics_exporter_enabled():
    """Returns whether to enable metrics exporting by default."""
    return _get_bool_flag_from_env(
        'OTEL_GCP_METRICS_EXPORTER_ENABLED',
        default_value=True
    )


def is_logs_exporter_enabled():
    """Returns whether to enable logs exporting by default."""
    return _get_bool_flag_from_env(
        'OTEL_GCP_LOGS_EXPORTER_ENABLED',
        default_value=True
    )


def is_traces_exporter_enabled():
    """Returns whether to enable trace exporting by default."""
    return _get_bool_flag_from_env(
        'OTEL_GCP_TRACES_EXPORTER_ENABLED',
        default_value=True
    )


def is_resource_detector_enabled():
    """Returns whether to enable the GCP resource detector by default."""
    result = _get_bool_flag_from_env(
        'OTEL_GCP_RESOURCE_DETECTOR_ENABLED')
    if result is not None:
        return result
    return gcloud_env.is_running_on_gcp()
