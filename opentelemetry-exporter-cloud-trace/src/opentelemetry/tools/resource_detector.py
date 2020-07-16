import os

import requests
from opentelemetry.context import attach, detach, set_value
from opentelemetry.sdk.resources import Resource, ResourceDetector

_GCP_METADATA_URL = (
    "http://metadata.google.internal/computeMetadata/v1/?recursive=true"
)
_GCP_METADATA_URL_HEADER = {"Metadata-Flavor": "Google"}


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
    # The user must specify these environment variables via the Downward API
    container_name = os.getenv("CONTAINER_NAME")
    pod_namespace = os.getenv("NAMESPACE")
    if not container_name or not pod_namespace:
        return {}
    (
        common_attributes,
        all_metadata,
    ) = _get_google_metadata_and_common_attributes()
    common_attributes.update(
        {
            "k8s.cluster.name": all_metadata["instance"]["attributes"][
                "cluster-name"
            ],
            "k8s.namespace.name": pod_namespace,
            "host.id": all_metadata["instance"]["id"],
            "k8s.pod.name": os.getenv("HOSTNAME", ""),
            "container.name": container_name,
            "gcp.resource_type": "gke_container",
        }
    )
    return common_attributes


# Order here matters. Since a GKE_CONTAINER is a specialized type of GCE_INSTANCE
# We need to first check if it matches the criteria for being a GKE_CONTAINER
# before falling back and checking if its a GCE_INSTANCE.
# This list should be sorted from most specialized to least specialized.
_RESOURCE_FINDERS = [get_gke_resources, get_gce_resources]


class GoogleCloudResourceDetector(ResourceDetector):
    def __init__(self, raise_on_error=False):
        super().__init__(raise_on_error)
        self.cached = False
        self.gcp_resources = {}

    def detect(self) -> "Resource":
        if not self.cached:
            self.cached = True
            for resource_finder in _RESOURCE_FINDERS:
                found_resources = resource_finder()
                if found_resources:
                    self.gcp_resources = found_resources
                    break
        return Resource(self.gcp_resources)
