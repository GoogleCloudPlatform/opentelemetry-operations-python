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
    get_cloudfunctions_resources,
    get_cloudrun_resources,
    get_gce_resources,
    get_gke_resources,
)
from opentelemetry.sdk.resources import Resource

NAMESPACE = "NAMESPACE"
CONTAINER_NAME = "CONTAINER_NAME"
HOSTNAME = "HOSTNAME"
POD_NAME = "POD_NAME"
KUBERNETES_SERVICE_HOST = "KUBERNETES_SERVICE_HOST"
K_CONFIGURATION = "K_CONFIGURATION"
FUNCTION_TARGET = "FUNCTION_TARGET"
K_SERVICE = "K_SERVICE"
K_REVISION = "K_REVISION"

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

CLOUDRUN_RESOURCES_JSON_STRING = {
    "instance": {
        "id": "instance_id",
        "zone": "projects/123/zones/zone",
        "region": "projects/123/regions/region",
    },
    "project": {"projectId": "project_id"},
}

CLOUDFUNCTIONS_RESOURCES_JSON_STRING = {
    "instance": {
        "id": "instance_id",
        "zone": "projects/123/zones/zone",
        "region": "projects/123/regions/region",
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


patch_env = mock.patch.dict(os.environ, {}, clear=True)


@patch_env
@mock.patch(
    "opentelemetry.resourcedetector.gcp_resource_detector.requests.get",
    **{"return_value.json.return_value": GKE_RESOURCES_JSON_STRING}
)
class TestGKEResourceFinder(unittest.TestCase):

    # pylint: disable=unused-argument
    def test_not_running_on_gke(self, getter):
        pop_environ_key(KUBERNETES_SERVICE_HOST)
        found_resources = get_gke_resources()
        self.assertEqual(found_resources, {})

    # pylint: disable=unused-argument
    def test_missing_container_name(self, getter):
        os.environ[KUBERNETES_SERVICE_HOST] = "10.0.0.1"
        pop_environ_key(CONTAINER_NAME)
        found_resources = get_gke_resources()
        self.assertEqual(
            found_resources,
            {
                "cloud.account.id": "project_id",
                "k8s.cluster.name": "cluster_name",
                "k8s.namespace.name": "",
                "host.id": "instance_id",
                "k8s.pod.name": "",
                "cloud.zone": "zone",
                "cloud.provider": "gcp",
                "gcp.resource_type": "gke_container",
            },
        )

    # pylint: disable=unused-argument
    def test_environment_empty_strings(self, getter):
        os.environ[KUBERNETES_SERVICE_HOST] = "10.0.0.1"
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
        os.environ[KUBERNETES_SERVICE_HOST] = "10.0.0.1"
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
        os.environ[KUBERNETES_SERVICE_HOST] = "10.0.0.1"
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
        os.environ[KUBERNETES_SERVICE_HOST] = "10.0.0.1"
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


@patch_env
@mock.patch(
    "opentelemetry.resourcedetector.gcp_resource_detector.requests.get",
    **{"return_value.json.return_value": CLOUDRUN_RESOURCES_JSON_STRING}
)
class TestCloudRunResourceFinder(unittest.TestCase):

    # pylint: disable=unused-argument
    def test_not_running_on_cloudrun(self, getter):
        pop_environ_key(K_CONFIGURATION)
        found_resources = get_cloudrun_resources()
        self.assertEqual(found_resources, {})

    # pylint: disable=unused-argument
    def test_missing_service_name(self, getter):
        os.environ[K_CONFIGURATION] = "cloudrun_config"
        pop_environ_key(K_SERVICE)
        pop_environ_key(K_REVISION)
        found_resources = get_cloudrun_resources()
        self.assertEqual(
            found_resources,
            {
                "cloud.account.id": "project_id",
                "cloud.platform": "gcp_cloud_run",
                "cloud.region": "region",
                "faas.instance": "instance_id",
                "cloud.zone": "zone",
                "cloud.provider": "gcp",
                "gcp.resource_type": "cloud_run",
            },
        )

    # pylint: disable=unused-argument
    def test_environment_empty_strings(self, getter):
        os.environ[K_CONFIGURATION] = "cloudrun_config"
        os.environ[K_SERVICE] = ""
        os.environ[K_REVISION] = ""
        found_resources = get_cloudrun_resources()
        self.assertEqual(
            found_resources,
            {
                "cloud.account.id": "project_id",
                "cloud.platform": "gcp_cloud_run",
                "cloud.region": "region",
                "faas.instance": "instance_id",
                "faas.name": "",
                "faas.version": "",
                "cloud.zone": "zone",
                "cloud.provider": "gcp",
                "gcp.resource_type": "cloud_run",
            },
        )

    def test_finding_cloudrun_resources(self, getter):
        os.environ[K_CONFIGURATION] = "cloudrun_config"
        os.environ[K_SERVICE] = "service"
        os.environ[K_REVISION] = "revision"
        found_resources = get_cloudrun_resources()
        self.assertEqual(getter.call_args_list[0][0][0], _GCP_METADATA_URL)
        self.assertEqual(
            found_resources,
            {
                "cloud.account.id": "project_id",
                "cloud.platform": "gcp_cloud_run",
                "cloud.region": "region",
                "faas.instance": "instance_id",
                "faas.name": "service",
                "faas.version": "revision",
                "cloud.zone": "zone",
                "cloud.provider": "gcp",
                "gcp.resource_type": "cloud_run",
            },
        )


@patch_env
@mock.patch(
    "opentelemetry.resourcedetector.gcp_resource_detector.requests.get",
    **{"return_value.json.return_value": CLOUDFUNCTIONS_RESOURCES_JSON_STRING}
)
class TestCloudFunctionsResourceFinder(unittest.TestCase):
    # pylint: disable=unused-argument
    def test_not_running_on_cloudfunctions(self, getter):
        pop_environ_key(FUNCTION_TARGET)
        found_resources = get_cloudfunctions_resources()
        self.assertEqual(found_resources, {})

    # pylint: disable=unused-argument
    def test_missing_service_name(self, getter):
        os.environ[FUNCTION_TARGET] = "function"
        pop_environ_key(K_SERVICE)
        pop_environ_key(K_REVISION)
        found_resources = get_cloudfunctions_resources()
        self.assertEqual(
            found_resources,
            {
                "cloud.account.id": "project_id",
                "cloud.platform": "gcp_cloud_functions",
                "cloud.region": "region",
                "faas.instance": "instance_id",
                "cloud.zone": "zone",
                "cloud.provider": "gcp",
                "gcp.resource_type": "cloud_functions",
            },
        )

    # pylint: disable=unused-argument
    def test_environment_empty_strings(self, getter):
        os.environ[FUNCTION_TARGET] = "function"
        os.environ[K_SERVICE] = ""
        os.environ[K_REVISION] = ""
        found_resources = get_cloudfunctions_resources()
        self.assertEqual(
            found_resources,
            {
                "cloud.account.id": "project_id",
                "cloud.platform": "gcp_cloud_functions",
                "cloud.region": "region",
                "faas.instance": "instance_id",
                "faas.name": "",
                "faas.version": "",
                "cloud.zone": "zone",
                "cloud.provider": "gcp",
                "gcp.resource_type": "cloud_functions",
            },
        )

    def test_finding_cloudfunctions_resources(self, getter):
        os.environ[FUNCTION_TARGET] = "function"
        os.environ[K_SERVICE] = "service"
        os.environ[K_REVISION] = "revision"
        found_resources = get_cloudfunctions_resources()
        self.assertEqual(getter.call_args_list[0][0][0], _GCP_METADATA_URL)
        self.assertEqual(
            found_resources,
            {
                "cloud.account.id": "project_id",
                "cloud.platform": "gcp_cloud_functions",
                "cloud.region": "region",
                "faas.instance": "instance_id",
                "faas.name": "service",
                "faas.version": "revision",
                "cloud.zone": "zone",
                "cloud.provider": "gcp",
                "gcp.resource_type": "cloud_functions",
            },
        )


@patch_env
@mock.patch(
    "opentelemetry.resourcedetector.gcp_resource_detector.requests.get"
)
class TestGoogleCloudResourceDetector(unittest.TestCase):
    def test_finding_gce_resources(self, getter):
        # The necessary env variables were not set for GKE resource detection
        # to succeed. We should be falling back to detecting GCE resources
        pop_environ_key(KUBERNETES_SERVICE_HOST)
        pop_environ_key(K_CONFIGURATION)
        pop_environ_key(FUNCTION_TARGET)
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
        os.environ[KUBERNETES_SERVICE_HOST] = "10.0.0.1"
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

    def test_finding_cloudrun_resources(self, getter):
        # The necessary env variables were set for CloudRun resource detection
        # to succeed. No GCE resource info should be extracted
        os.environ[K_CONFIGURATION] = "cloudrun_config"
        os.environ[K_SERVICE] = "service"
        os.environ[K_REVISION] = "revision"

        resource_finder = GoogleCloudResourceDetector()
        getter.return_value.json.return_value = CLOUDRUN_RESOURCES_JSON_STRING
        found_resources = resource_finder.detect()
        self.assertEqual(getter.call_args_list[0][0][0], _GCP_METADATA_URL)
        self.assertEqual(
            found_resources,
            Resource(
                attributes={
                    "cloud.account.id": "project_id",
                    "cloud.platform": "gcp_cloud_run",
                    "cloud.region": "region",
                    "faas.instance": "instance_id",
                    "faas.name": "service",
                    "faas.version": "revision",
                    "cloud.zone": "zone",
                    "cloud.provider": "gcp",
                    "gcp.resource_type": "cloud_run",
                }
            ),
        )
        self.assertEqual(getter.call_count, 1)

    def test_finding_cloudfunctions_resources(self, getter):
        # The necessary env variables were set for Cloudfunctions resource detection
        # to succeed. No GCE resource info should be extracted
        os.environ[FUNCTION_TARGET] = "function"
        os.environ[K_SERVICE] = "service"
        os.environ[K_REVISION] = "revision"

        resource_finder = GoogleCloudResourceDetector()
        getter.return_value.json.return_value = (
            CLOUDFUNCTIONS_RESOURCES_JSON_STRING
        )
        found_resources = resource_finder.detect()
        self.assertEqual(getter.call_args_list[0][0][0], _GCP_METADATA_URL)
        self.assertEqual(
            found_resources,
            Resource(
                attributes={
                    "cloud.account.id": "project_id",
                    "cloud.platform": "gcp_cloud_functions",
                    "cloud.region": "region",
                    "faas.instance": "instance_id",
                    "faas.name": "service",
                    "faas.version": "revision",
                    "cloud.zone": "zone",
                    "cloud.provider": "gcp",
                    "gcp.resource_type": "cloud_functions",
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

        resource_finder = GoogleCloudResourceDetector(raise_on_error=True)

        self.assertRaises(NoGoogleResourcesFound, resource_finder.detect)

    def test_detector_dont_raise_on_error(self, getter):
        # If no Google resources were found, we throw an exception
        getter.return_value.json.side_effect = Exception
        detector = GoogleCloudResourceDetector(raise_on_error=False)
        expected_resources = Resource({})

        resources = detector.detect()

        self.assertEqual(resources, expected_resources)
