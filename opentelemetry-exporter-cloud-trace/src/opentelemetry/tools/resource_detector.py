import logging
import os

import requests
from opentelemetry.context import attach, detach, set_value
from opentelemetry.sdk.resources import Resource, ResourceDetector

_GCP_METADATA_URL = (
    "http://metadata.google.internal/computeMetadata/v1/?recursive=true"
)
_GCP_METADATA_URL_HEADER = {"Metadata-Flavor": "Google"}

logger = logging.getLogger(__name__)


def _get_google_metadata_and_common_attributes():
    token = attach(set_value("suppress_instrumentation", True))
    all_metadata = requests.get(
        _GCP_METADATA_URL, headers=_GCP_METADATA_URL_HEADER
    ).json()
    detach(token)
    common_attributes = {
        "cloud.account.id": all_metadata["project"]["projectId"],
        "cloud.provider": "gcp",
        "cloud.zone": all_metadata["instance"]["zone"].split("/")[-1],
    }
    return common_attributes, all_metadata


def get_gce_resources():
    """ Resource finder for common GCE attributes

        See: https://cloud.google.com/compute/docs/storing-retrieving-metadata
    """
    (
        common_attributes,
        all_metadata,
    ) = _get_google_metadata_and_common_attributes()
    common_attributes.update(
        {
            "host.id": all_metadata["instance"]["id"],
            "gcp.resource_type": "gce_instance",
        }
    )
    return common_attributes


def get_gke_resources():
    """ Resource finder for GKE attributes

    """
    # The user must specify the container name via the Downward API
    container_name = os.getenv("CONTAINER_NAME")
    if container_name is None:
        return {}
    (
        common_attributes,
        all_metadata,
    ) = _get_google_metadata_and_common_attributes()

    # Fallback to reading namespace from a file is the env var is not set
    pod_namespace = os.getenv("NAMESPACE")
    if pod_namespace is None:
        try:
            with open(
                "/var/run/secrets/kubernetes.io/serviceaccount/namespace", "r"
            ) as namespace_file:
                pod_namespace = namespace_file.read().strip()
        except FileNotFoundError:
            pod_namespace = ""

    common_attributes.update(
        {
            "k8s.cluster.name": all_metadata["instance"]["attributes"][
                "cluster-name"
            ],
            "k8s.namespace.name": pod_namespace,
            "k8s.pod.name": os.getenv("POD_NAME", os.getenv("HOSTNAME", "")),
            "host.id": all_metadata["instance"]["id"],
            "container.name": container_name,
            "gcp.resource_type": "gke_container",
        }
    )
    return common_attributes


# Order here matters. Since a GKE_CONTAINER is a specialized type of GCE_INSTANCE
# We need to first check if it matches the criteria for being a GKE_CONTAINER
# before falling back and checking if its a GCE_INSTANCE.
# This list should be sorted from most specialized to least specialized.
_RESOURCE_FINDERS = [
    ("gke_container", get_gke_resources),
    ("gce_instance", get_gce_resources),
]


class NoGoogleResourcesFound(Exception):
    pass


class GoogleCloudResourceDetector(ResourceDetector):
    def __init__(self, raise_on_error=False):
        super().__init__(raise_on_error)
        self.cached = False
        self.gcp_resources = {}

    def detect(self) -> "Resource":
        if not self.cached:
            self.cached = True
            for resource_type, resource_finder in _RESOURCE_FINDERS:
                try:
                    found_resources = resource_finder()
                # pylint: disable=broad-except
                except Exception as ex:
                    logger.warning(
                        "Exception %s occured attempting %s resource detection",
                        ex,
                        resource_type,
                    )
                    found_resources = None
                if found_resources:
                    self.gcp_resources = found_resources
                    break
        if not self.gcp_resources:
            raise NoGoogleResourcesFound()
        return Resource(self.gcp_resources)
