# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import os

import requests
from opentelemetry.context import attach, detach, set_value
from opentelemetry.sdk.resources import Resource, ResourceDetector

_GCP_METADATA_URL = (
    "http://metadata.google.internal/computeMetadata/v1/?recursive=true"
)
_GCP_METADATA_URL_HEADER = {"Metadata-Flavor": "Google"}
_TIMEOUT_SEC = 5

logger = logging.getLogger(__name__)


def _get_google_metadata_and_common_attributes():
    token = attach(set_value("suppress_instrumentation", True))
    all_metadata = requests.get(
        _GCP_METADATA_URL,
        headers=_GCP_METADATA_URL_HEADER,
        timeout=_TIMEOUT_SEC,
    ).json()
    detach(token)
    common_attributes = {
        "cloud.account.id": all_metadata["project"]["projectId"],
        "cloud.provider": "gcp",
        "cloud.zone": all_metadata["instance"]["zone"].split("/")[-1],
    }
    return common_attributes, all_metadata


def get_gce_resources():
    """Resource finder for common GCE attributes

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
    """Resource finder for GKE attributes"""

    if os.getenv("KUBERNETES_SERVICE_HOST") is None:
        return {}

    (
        common_attributes,
        all_metadata,
    ) = _get_google_metadata_and_common_attributes()

    container_name = os.getenv("CONTAINER_NAME")
    if container_name is not None:
        common_attributes["container.name"] = container_name

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
            "gcp.resource_type": "gke_container",
        }
    )
    return common_attributes


def get_cloudrun_resources():
    """Resource finder for Cloud Run attributes"""

    if os.getenv("K_CONFIGURATION") is None:
        return {}

    (
        common_attributes,
        all_metadata,
    ) = _get_google_metadata_and_common_attributes()

    faas_name = os.getenv("K_SERVICE")
    if faas_name is not None:
        common_attributes["faas.name"] = str(faas_name)

    faas_version = os.getenv("K_REVISION")
    if faas_version is not None:
        common_attributes["faas.version"] = str(faas_version)

    common_attributes.update(
        {
            "cloud.platform": "gcp_cloud_run",
            "cloud.region": all_metadata["instance"]["region"].split("/")[-1],
            "faas.instance": all_metadata["instance"]["id"],
            "gcp.resource_type": "cloud_run",
        }
    )
    return common_attributes


def get_cloudfunctions_resources():
    """Resource finder for Cloud Functions attributes"""

    if os.getenv("FUNCTION_TARGET") is None:
        return {}

    (
        common_attributes,
        all_metadata,
    ) = _get_google_metadata_and_common_attributes()

    faas_name = os.getenv("K_SERVICE")
    if faas_name is not None:
        common_attributes["faas.name"] = str(faas_name)

    faas_version = os.getenv("K_REVISION")
    if faas_version is not None:
        common_attributes["faas.version"] = str(faas_version)

    common_attributes.update(
        {
            "cloud.platform": "gcp_cloud_functions",
            "cloud.region": all_metadata["instance"]["region"].split("/")[-1],
            "faas.instance": all_metadata["instance"]["id"],
            "gcp.resource_type": "cloud_functions",
        }
    )
    return common_attributes


# Order here matters. Since a GKE_CONTAINER is a specialized type of GCE_INSTANCE
# We need to first check if it matches the criteria for being a GKE_CONTAINER
# before falling back and checking if its a GCE_INSTANCE.
# This list should be sorted from most specialized to least specialized.
_RESOURCE_FINDERS = [
    ("gke_container", get_gke_resources),
    ("cloud_run", get_cloudrun_resources),
    ("cloud_functions", get_cloudfunctions_resources),
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
        if self.raise_on_error and not self.gcp_resources:
            raise NoGoogleResourcesFound()
        return Resource(self.gcp_resources)
