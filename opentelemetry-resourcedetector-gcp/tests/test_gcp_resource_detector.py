# Copyright 2021 The OpenTelemetry Authors
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

import os
import unittest
from unittest import mock

from opentelemetry.resourcedetector.gcp_resource_detector import (
    _GCP_METADATA_URL,
    GoogleCloudResourceDetector,
    NoGoogleResourcesFound,
    get_gce_resources,
    get_gke_resources,
)
from opentelemetry.sdk.resources import Resource

NAMESPACE = "NAMESPACE"
CONTAINER_NAME = "CONTAINER_NAME"
HOSTNAME = "HOSTNAME"
POD_NAME = "POD_NAME"

GCE_RESOURCES_JSON_STRING = {
    "instance": {"id": "instance_id", "zone": "projects/123/zones/zone"},
    "project": {"projectId": "project_id"},
}

GKE_RESOURCES_JSON_STRING = {
    "instance": {
        "id": "instance_id",
        "zone": "projects/123/zones/zone",
        "attributes": {"cluster-name": "cluster_name"},
    },
    "project": {"projectId": "project_id"},
}


@mock.patch(
    "opentelemetry.resourcedetector.gcp_resource_detector.requests.get",
    **{"return_value.json.return_value": GCE_RESOURCES_JSON_STRING}
)
class TestGCEResourceFinder(unittest.TestCase):
    def test_finding_gce_resources(self, getter):
        found_resources = get_gce_resources()
        self.assertEqual(getter.call_args_list[0][0][0], _GCP_METADATA_URL)
        self.assertEqual(
            found_resources,
            {
                "host.id": "instance_id",
                "cloud.provider": "gcp",
                "cloud.account.id": "project_id",
                "cloud.zone": "zone",
                "gcp.resource_type": "gce_instance",
            },
        )


def pop_environ_key(key):
    if key in os.environ:
        os.environ.pop(key)


def clear_gke_env_vars():
    pop_environ_key(CONTAINER_NAME)
    pop_environ_key(NAMESPACE)
    pop_environ_key(HOSTNAME)
    pop_environ_key(POD_NAME)


@mock.patch(
    "opentelemetry.resourcedetector.gcp_resource_detector.requests.get",
    **{"return_value.json.return_value": GKE_RESOURCES_JSON_STRING}
)
class TestGKEResourceFinder(unittest.TestCase):
    def tearDown(self) -> None:
        clear_gke_env_vars()

    # pylint: disable=unused-argument
    def test_missing_container_name(self, getter):
        pop_environ_key(CONTAINER_NAME)
        self.assertEqual(get_gke_resources(), {})

    # pylint: disable=unused-argument
    def test_environment_empty_strings(self, getter):
        os.environ[CONTAINER_NAME] = ""
        os.environ[NAMESPACE] = ""
        found_resources = get_gke_resources()
        self.assertEqual(
            found_resources,
            {
                "cloud.account.id": "project_id",
                "k8s.cluster.name": "cluster_name",
                "k8s.namespace.name": "",
                "host.id": "instance_id",
                "k8s.pod.name": "",
                "container.name": "",
                "cloud.zone": "zone",
                "cloud.provider": "gcp",
                "gcp.resource_type": "gke_container",
            },
        )

    def test_missing_namespace_file(self, getter):
        os.environ[CONTAINER_NAME] = "container_name"
        found_resources = get_gke_resources()
        self.assertEqual(
            found_resources,
            {
                "cloud.account.id": "project_id",
                "k8s.cluster.name": "cluster_name",
                "k8s.namespace.name": "",
                "host.id": "instance_id",
                "k8s.pod.name": "",
                "container.name": "container_name",
                "cloud.zone": "zone",
                "cloud.provider": "gcp",
                "gcp.resource_type": "gke_container",
            },
        )

    def test_finding_gke_resources(self, getter):
        os.environ[NAMESPACE] = "namespace"
        os.environ[CONTAINER_NAME] = "container_name"
        os.environ[HOSTNAME] = "host_name"
        found_resources = get_gke_resources()
        self.assertEqual(getter.call_args_list[0][0][0], _GCP_METADATA_URL)
        self.assertEqual(
            found_resources,
            {
                "cloud.account.id": "project_id",
                "k8s.cluster.name": "cluster_name",
                "k8s.namespace.name": "namespace",
                "host.id": "instance_id",
                "k8s.pod.name": "host_name",
                "container.name": "container_name",
                "cloud.zone": "zone",
                "cloud.provider": "gcp",
                "gcp.resource_type": "gke_container",
            },
        )

    def test_finding_gke_resources_with_pod_name(self, getter):
        os.environ[NAMESPACE] = "namespace"
        os.environ[CONTAINER_NAME] = "container_name"
        os.environ[HOSTNAME] = "host_name"
        os.environ[POD_NAME] = "pod_name"
        found_resources = get_gke_resources()
        self.assertEqual(getter.call_args_list[0][0][0], _GCP_METADATA_URL)
        self.assertEqual(
            found_resources,
            {
                "cloud.account.id": "project_id",
                "k8s.cluster.name": "cluster_name",
                "k8s.namespace.name": "namespace",
                "host.id": "instance_id",
                "k8s.pod.name": "pod_name",
                "container.name": "container_name",
                "cloud.zone": "zone",
                "cloud.provider": "gcp",
                "gcp.resource_type": "gke_container",
            },
        )


@mock.patch(
    "opentelemetry.resourcedetector.gcp_resource_detector.requests.get"
)
class TestGoogleCloudResourceDetector(unittest.TestCase):
    def tearDown(self) -> None:
        clear_gke_env_vars()

    def test_finding_gce_resources(self, getter):
        # The necessary env variables were not set for GKE resource detection
        # to succeed. We should be falling back to detecting GCE resources
        resource_finder = GoogleCloudResourceDetector()
        getter.return_value.json.return_value = GCE_RESOURCES_JSON_STRING
        found_resources = resource_finder.detect()
        self.assertEqual(getter.call_args_list[0][0][0], _GCP_METADATA_URL)
        self.assertEqual(
            found_resources,
            Resource(
                attributes={
                    "host.id": "instance_id",
                    "cloud.provider": "gcp",
                    "cloud.account.id": "project_id",
                    "cloud.zone": "zone",
                    "gcp.resource_type": "gce_instance",
                }
            ),
        )
        self.assertEqual(getter.call_count, 1)

        # Found resources should be cached and not require another network call
        found_resources = resource_finder.detect()
        self.assertEqual(getter.call_count, 1)
        self.assertEqual(
            found_resources,
            Resource(
                attributes={
                    "host.id": "instance_id",
                    "cloud.provider": "gcp",
                    "cloud.account.id": "project_id",
                    "cloud.zone": "zone",
                    "gcp.resource_type": "gce_instance",
                }
            ),
        )

    def test_finding_gke_resources(self, getter):
        # The necessary env variables were set for GKE resource detection
        # to succeed. No GCE resource info should be extracted

        os.environ[NAMESPACE] = "namespace"
        os.environ[CONTAINER_NAME] = "container_name"
        os.environ[HOSTNAME] = "host_name"

        resource_finder = GoogleCloudResourceDetector()
        getter.return_value.json.return_value = GKE_RESOURCES_JSON_STRING
        found_resources = resource_finder.detect()
        self.assertEqual(getter.call_args_list[0][0][0], _GCP_METADATA_URL)
        self.assertEqual(
            found_resources,
            Resource(
                attributes={
                    "cloud.account.id": "project_id",
                    "k8s.cluster.name": "cluster_name",
                    "k8s.namespace.name": "namespace",
                    "host.id": "instance_id",
                    "k8s.pod.name": "host_name",
                    "container.name": "container_name",
                    "cloud.zone": "zone",
                    "cloud.provider": "gcp",
                    "gcp.resource_type": "gke_container",
                }
            ),
        )
        self.assertEqual(getter.call_count, 1)

    def test_resource_finding_fallback(self, getter):
        # The environment variables imply its on GKE, but the metadata doesn't
        # have GKE information
        getter.return_value.json.return_value = GCE_RESOURCES_JSON_STRING
        os.environ[CONTAINER_NAME] = "container_name"

        # This detection will cause an error in get_gke_resources and should
        # swallow the error and fall back to get_gce_resources
        resource_finder = GoogleCloudResourceDetector()
        found_resources = resource_finder.detect()
        self.assertEqual(
            found_resources,
            Resource(
                attributes={
                    "host.id": "instance_id",
                    "cloud.provider": "gcp",
                    "cloud.account.id": "project_id",
                    "cloud.zone": "zone",
                    "gcp.resource_type": "gce_instance",
                }
            ),
        )

    def test_no_resources_found(self, getter):
        # If no Google resources were found, we throw an exception
        getter.return_value.json.side_effect = Exception
        resource_finder = GoogleCloudResourceDetector()
        self.assertRaises(NoGoogleResourcesFound, resource_finder.detect)
