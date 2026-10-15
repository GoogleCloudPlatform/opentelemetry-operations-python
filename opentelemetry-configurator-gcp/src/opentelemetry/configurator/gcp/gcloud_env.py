"""Provides 'is_running_on_gcp' to determine whether to enable the GCP resource detector."""
import os
import os.path
import socket


def _can_resolve_metadata_server():
    """Returns whether the GCP metadata server address can be resolved.
    
    On GCP, there is a special 'metadata.google.internal' DNS name that is
    used to supply metadata about the environment. Although it is possible
    to edit "/etc/hosts" to introduce a similarly-named service outside
    of GCP, the existence of this name is a strong hint of running in GCP.
    """
    try:
        socket.getaddrinfo('metadata.google.internal', 80)
        return True
    except OSError:
        return False


def _is_likely_gae():
    """Returns whether env vars indicate a GAE environment.

    The Google App Engine documentation calls out several of these
    environment variables as being automatically setup by the runtime.

    Although it is possible to set these manually outside of GAE, the
    presence of these in conjunction with the presence of the metadata
    server provides a strong hint of running within GAE.
    """
    return (('GAE_APPLICATION' in os.environ) and
            ('GAE_DEPLOYMENT_ID' in os.environ) and
            ('GAE_SERVICE' in os.environ))


def _is_likely_cloud_run():
    """Returns whether env vars indicate a Cloud Run environment.

    The Cloud Run documentation calls out several of these
    environment variables as being automatically setup by the runtime.

    Some of these may aslo be present when running K-Native in Kubernetes;
    however, the presence of these environment variables in conjunction
    with the presence of the metadata server provide a strong hint
    that the code is running inside of Cloud Run.
    """
    return (
        ('K_SERVICE' in os.environ) and
        ('K_REVISION' in os.environ) and
        ('K_CONFIGURATION' in os.environ))


def _is_likely_gce():
    """Returns whether there is evidence of running in GCE.
    
    The given pre-supplied paths are called out in GCE documentation
    and are not likely to exist in other environments. In conjunction
    with the existing of the metadata server, the checks here provide
    supportive evidence of running within a GCE environment.
    """
    return os.path.exists('/run/google-mds-mtls')


def _is_likely_gke():
    """Returns whether there is evidence of runing in GKE.

    Although also applicable to Kubernetes outside of GCP,
    the evidence of Kubernetes in conjunction with the presence
    of the GCP metadata server strongly hints at GKE.
    """
    return 'KUBERNETES_SERVICE_HOST' in os.environ


def is_running_on_gcp():
    """Returns whether the code is probably running on GCP.
    
    This is not intended to be 100% bullet proof nor
    comprehensive of the entire GCP ecosystem; rather, it
    is intended to be "good enough" to determine whether to
    pay the additional costs of GCP resource detection.

    That is, it should ideally be light-weight (if it's too
    expensive, you might as well always do GCP resource
    detection), and it should ideally cover the subset
    of GCP environments for which resource detction exists.
    """
    return (
        _can_resolve_metadata_server() and
        (
            _is_likely_gke() or
            _is_likely_cloud_run() or
            _is_likely_gce() or
            _is_likely_gae()
        )
    )
