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


def is_running_on_gcp():
    return (
        _can_resolve_metadata_server() and
        (
            _is_likely_gke() or
            _is_likely_cloud_run() or
            _is_likely_gce() or
            _is_likely_gae()
        )
    )

