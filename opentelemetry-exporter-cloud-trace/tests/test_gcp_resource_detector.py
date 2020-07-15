# Copyright The OpenTelemetry Authors
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

from opentelemetry.sdk.resources import Resource
from opentelemetry.tools.resource_detector import (
    _GCP_METADATA_URL,
    GoogleCloudResourceDetector,
    get_gce_resources,
    get_gke_resources,
)

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


class TestGCEResourceFinder(unittest.TestCase):
    @mock.patch("opentelemetry.tools.resource_detector.requests.get")
    def test_finding_gce_resources(self, getter):
        getter.return_value.json.return_value = GCE_RESOURCES_JSON_STRING
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
    pop_environ_key("CONTAINER_NAME")
    pop_environ_key("NAMESPACE")
    pop_environ_key("HOSTNAME")


class TestGKEResourceFinder(unittest.TestCase):
    def tearDown(self) -> None:
        clear_gke_env_vars()

    @mock.patch("opentelemetry.tools.resource_detector.requests.get")
    def test_missing_environment_variables(self, getter):
        getter.return_value.json.return_value = GKE_RESOURCES_JSON_STRING

        # If one of CONTAINER_NAME, NAMESPACE is missing from the environment
        # return no resources

        pop_environ_key("CONTAINER_NAME")
        pop_environ_key("NAMESPACE")
        self.assertEqual(get_gke_resources(), {})

        os.environ["NAMESPACE"] = "namespace"
        self.assertEqual(get_gke_resources(), {})

        pop_environ_key("NAMESPACE")
        os.environ["CONTAINER_NAME"] = "container_name"
        self.assertEqual(get_gke_resources(), {})
        clear_gke_env_vars()

    @mock.patch("opentelemetry.tools.resource_detector.requests.get")
    def test_finding_gke_resources(self, getter):
        os.environ["NAMESPACE"] = "namespace"
        os.environ["CONTAINER_NAME"] = "container_name"
        os.environ["HOSTNAME"] = "host_name"
        getter.return_value.json.return_value = GKE_RESOURCES_JSON_STRING
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
        clear_gke_env_vars()


class TestGoogleCloudResourceDetector(unittest.TestCase):
    def tearDown(self) -> None:
        clear_gke_env_vars()

    @mock.patch("opentelemetry.tools.resource_detector.requests.get")
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
                labels={
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
                labels={
                    "host.id": "instance_id",
                    "cloud.provider": "gcp",
                    "cloud.account.id": "project_id",
                    "cloud.zone": "zone",
                    "gcp.resource_type": "gce_instance",
                }
            ),
        )

    @mock.patch("opentelemetry.tools.resource_detector.requests.get")
    def test_finding_gke_resources(self, getter):
        # The necessary env variables were set for GKE resource detection
        # to succeed. No GCE resource info should be extracted

        os.environ["NAMESPACE"] = "namespace"
        os.environ["CONTAINER_NAME"] = "container_name"
        os.environ["HOSTNAME"] = "host_name"

        resource_finder = GoogleCloudResourceDetector()
        getter.return_value.json.return_value = GKE_RESOURCES_JSON_STRING
        found_resources = resource_finder.detect()
        self.assertEqual(getter.call_args_list[0][0][0], _GCP_METADATA_URL)
        self.assertEqual(
            found_resources,
            Resource(
                labels={
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
        clear_gke_env_vars()
