import gcloud_env


def _str_to_optional_bool(s):
    lower_s = s.lower()
    if lower_s in ['1', 'true', 't', 'y', 'yes', 'on']:
        return True
    if lower_s in ['0', 'false', 'f', 'n', 'no', 'off']:
        return False
    return None


def _get_bool_flag_from_env(env_var_name, default_value=None):
    s = os.getenv(env_var_name)
    if s is None:
        return default_value
    result = _str_to_optional_bool(s)
    if result is not None:
        return result
    return default_value


def is_metrics_exporter_enabled():
    return _get_bool_flag_from_env(
        'OTEL_GCP_METRICS_EXPORTER_ENABLED',
        default_value=True
    )


def is_logs_exporter_enabled():
    return _get_bool_flag_from_env(
        'OTEL_GCP_LOGS_EXPORTER_ENABLED',
        default_value=True
    )


def is_traces_exporter_enabled():
    return _get_bool_flag_from_env(
        'OTEL_GCP_TRACES_EXPORTER_ENABLED',
        default_value=True
    )


def is_resource_detector_enabled():
    result = _get_bool_flag_from_env(
        'OTEL_GCP_RESOURCE_DETECTOR_ENABLED')
    if result is not None:
        return result
    return gcloud_env.is_running_on_gcp()
