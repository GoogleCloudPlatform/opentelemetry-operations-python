# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import Mapping

from opentelemetry.resourcedetector.gcp_resource_detector import (
    _gce,
    _metadata,
)
from opentelemetry.sdk.resources import Resource, ResourceDetector
from opentelemetry.util.types import AttributeValue


# TODO: use opentelemetry-semantic-conventions package for these constants once it has
# stabilized. Right now, pinning an unstable version would cause dependency conflicts for
# users so these are copied in.
class ResourceAttributes:
    AWS_EC2 = "aws_ec2"
    CLOUD_ACCOUNT_ID = "cloud.account.id"
    CLOUD_AVAILABILITY_ZONE = "cloud.availability_zone"
    CLOUD_PLATFORM_KEY = "cloud.platform"
    CLOUD_PROVIDER = "cloud.provider"
    CLOUD_REGION = "cloud.region"
    GCP_COMPUTE_ENGINE = "gcp_compute_engine"
    GCP_KUBERNETES_ENGINE = "gcp_kubernetes_engine"
    HOST_ID = "host.id"
    HOST_NAME = "host.name"
    HOST_TYPE = "host.type"
    K8S_CLUSTER_NAME = "k8s.cluster.name"
    K8S_CONTAINER_NAME = "k8s.container.name"
    K8S_NAMESPACE_NAME = "k8s.namespace.name"
    K8S_NODE_NAME = "k8s.node.name"
    K8S_POD_NAME = "k8s.pod.name"
    SERVICE_INSTANCE_ID = "service.instance.id"
    SERVICE_NAME = "service.name"
    SERVICE_NAMESPACE = "service.namespace"


class GoogleCloudResourceDetector(ResourceDetector):
    def detect(self) -> Resource:
        if not _metadata.is_available():
            return Resource.get_empty()

        if _gce.on_gce():
            return _gce_resource()

        return Resource.get_empty()


def _gce_resource() -> Resource:
    zone_and_region = _gce.availability_zone_and_region()
    return _make_resource(
        {
            ResourceAttributes.CLOUD_PLATFORM_KEY: ResourceAttributes.GCP_COMPUTE_ENGINE,
            ResourceAttributes.CLOUD_AVAILABILITY_ZONE: zone_and_region.zone,
            ResourceAttributes.CLOUD_REGION: zone_and_region.region,
            ResourceAttributes.HOST_TYPE: _gce.host_type(),
            ResourceAttributes.HOST_ID: _gce.host_id(),
            ResourceAttributes.HOST_NAME: _gce.host_name(),
        }
    )


def _make_resource(attrs: Mapping[str, AttributeValue]) -> Resource:
    return Resource.create(
        {
            ResourceAttributes.CLOUD_PROVIDER: "gcp",
            ResourceAttributes.CLOUD_ACCOUNT_ID: _metadata.get_metadata()[
                "project"
            ]["projectId"],
            **attrs,
        }
    )
