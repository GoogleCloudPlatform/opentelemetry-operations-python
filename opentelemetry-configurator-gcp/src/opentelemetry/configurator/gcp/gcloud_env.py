import os
import os.path
import socket


def _can_resolve_metadata_server():
    try:
        socket.getaddrinfo('metadata.google.internal', 80)
        return True
    except:
        return False


def _is_likely_gae():
    return (('GAE_APPLICATION' in os.environ) and
            ('GAE_DEPLOYMENT_ID' in os.environ) and
            ('GAE_SERVICE' in os.environ))


def _is_likely_cloud_run():
    return (
        ('K_SERVICE' in os.environ) and
        ('K_REVISION' in os.environ) and
        ('K_CONFIGURATION' in os.environ))


def _is_likely_gce():
    return os.path.exists('/run/google-mds-mtls')


def _is_likely_gke():
    return ('KUBERNETES_SERVICE_HOST' in os.environ)


_NOT_GOOGLE_CLOUD = 'NOT_GCLOUD'
_GAE = 'GOOGLE_APP_ENGINE'
_CLOUD_RUN = 'CLOUD_RUN'
_GKE = 'GKE'
_GCE = 'GCE'

_detected_environ = None

def _detect_environ():
    global _detected_environ
    if _detected_environ is not None:
        return _detected_environ
    if not _can_resolve_metadata_server():
        _detected_environ = _NOT_GOOGLE_CLOUD
    elif _is_likely_gae():
        _detected_environ = _GAE
    elif _is_likely_gke():
        _detected_environ = _GKE
    elif _is_likely_cloud_run():
        _detected_environ = _CLOUD_RUN
    elif _is_likely_gce():
        _detected_environ = _GCE
    else:
        _detected_environ  = _NOT_GOOGLE_CLOUD
    return _detected_environ


def is_running_on_gcp():
    return _detect_environ() != _NOT_GOOGLE_CLOUD
