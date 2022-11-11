# Copyright 2022 Google LLC
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

import json
from typing import Dict, Optional, Tuple

from google.api.monitored_resource_pb2 import MonitoredResource
from opentelemetry.sdk.resources import Attributes, Resource


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
    K8S_CLUSTER_NAME = "k8s.cluster.name"
    K8S_CONTAINER_NAME = "k8s.container.name"
    K8S_NAMESPACE_NAME = "k8s.namespace.name"
    K8S_NODE_NAME = "k8s.node.name"
    K8S_POD_NAME = "k8s.pod.name"
    SERVICE_INSTANCE_ID = "service.instance.id"
    SERVICE_NAME = "service.name"
    SERVICE_NAMESPACE = "service.namespace"


AWS_ACCOUNT = "aws_account"
AWS_EC2_INSTANCE = "aws_ec2_instance"
CLUSTER_NAME = "cluster_name"
CONTAINER_NAME = "container_name"
GCE_INSTANCE = "gce_instance"
GENERIC_NODE = "generic_node"
GENERIC_TASK = "generic_task"
INSTANCE_ID = "instance_id"
JOB = "job"
K8S_CLUSTER = "k8s_cluster"
K8S_CONTAINER = "k8s_container"
K8S_NODE = "k8s_node"
K8S_POD = "k8s_pod"
LOCATION = "location"
NAMESPACE = "namespace"
NAMESPACE_NAME = "namespace_name"
NODE_ID = "node_id"
NODE_NAME = "node_name"
POD_NAME = "pod_name"
REGION = "region"
TASK_ID = "task_id"
ZONE = "zone"


class MapConfig:
    otel_keys: Tuple[str, ...]
    """
    OTel resource keys to try and populate the resource label from. For entries with multiple
    OTel resource keys, the keys' values will be coalesced in order until there is a non-empty
    value.
    """

    fallback: str
    """If none of the otelKeys are present in the Resource, fallback to this literal value"""

    def __init__(self, *otel_keys: str, fallback: str = ""):
        self.otel_keys = otel_keys
        self.fallback = fallback


# Mappings of GCM resource label keys onto mapping config from OTel resource for a given
# monitored resource type. Copied from Go impl:
# https://github.com/GoogleCloudPlatform/opentelemetry-operations-go/blob/v1.8.0/internal/resourcemapping/resourcemapping.go#L51
MAPPINGS = {
    GCE_INSTANCE: {
        ZONE: MapConfig(ResourceAttributes.CLOUD_AVAILABILITY_ZONE),
        INSTANCE_ID: MapConfig(ResourceAttributes.HOST_ID),
    },
    K8S_CONTAINER: {
        LOCATION: MapConfig(
            ResourceAttributes.CLOUD_AVAILABILITY_ZONE,
            ResourceAttributes.CLOUD_REGION,
        ),
        CLUSTER_NAME: MapConfig(ResourceAttributes.K8S_CLUSTER_NAME),
        NAMESPACE_NAME: MapConfig(ResourceAttributes.K8S_NAMESPACE_NAME),
        POD_NAME: MapConfig(ResourceAttributes.K8S_POD_NAME),
        CONTAINER_NAME: MapConfig(ResourceAttributes.K8S_CONTAINER_NAME),
    },
    K8S_POD: {
        LOCATION: MapConfig(
            ResourceAttributes.CLOUD_AVAILABILITY_ZONE,
            ResourceAttributes.CLOUD_REGION,
        ),
        CLUSTER_NAME: MapConfig(ResourceAttributes.K8S_CLUSTER_NAME),
        NAMESPACE_NAME: MapConfig(ResourceAttributes.K8S_NAMESPACE_NAME),
        POD_NAME: MapConfig(ResourceAttributes.K8S_POD_NAME),
    },
    K8S_NODE: {
        LOCATION: MapConfig(
            ResourceAttributes.CLOUD_AVAILABILITY_ZONE,
            ResourceAttributes.CLOUD_REGION,
        ),
        CLUSTER_NAME: MapConfig(ResourceAttributes.K8S_CLUSTER_NAME),
        NODE_NAME: MapConfig(ResourceAttributes.K8S_NODE_NAME),
    },
    K8S_CLUSTER: {
        LOCATION: MapConfig(
            ResourceAttributes.CLOUD_AVAILABILITY_ZONE,
            ResourceAttributes.CLOUD_REGION,
        ),
        CLUSTER_NAME: MapConfig(ResourceAttributes.K8S_CLUSTER_NAME),
    },
    AWS_EC2_INSTANCE: {
        INSTANCE_ID: MapConfig(ResourceAttributes.HOST_ID),
        REGION: MapConfig(
            ResourceAttributes.CLOUD_AVAILABILITY_ZONE,
            ResourceAttributes.CLOUD_REGION,
        ),
        AWS_ACCOUNT: MapConfig(ResourceAttributes.CLOUD_ACCOUNT_ID),
    },
    GENERIC_TASK: {
        LOCATION: MapConfig(
            ResourceAttributes.CLOUD_AVAILABILITY_ZONE,
            ResourceAttributes.CLOUD_REGION,
            fallback="global",
        ),
        NAMESPACE: MapConfig(ResourceAttributes.SERVICE_NAMESPACE),
        JOB: MapConfig(ResourceAttributes.SERVICE_NAME),
        TASK_ID: MapConfig(ResourceAttributes.SERVICE_INSTANCE_ID),
    },
    GENERIC_NODE: {
        LOCATION: MapConfig(
            ResourceAttributes.CLOUD_AVAILABILITY_ZONE,
            ResourceAttributes.CLOUD_REGION,
            fallback="global",
        ),
        NAMESPACE: MapConfig(ResourceAttributes.SERVICE_NAMESPACE),
        NODE_ID: MapConfig(
            ResourceAttributes.HOST_ID, ResourceAttributes.HOST_NAME
        ),
    },
}


def get_monitored_resource(
    resource: Resource,
) -> Optional[MonitoredResource]:
    """Add Google resource specific information (e.g. instance id, region).

    See
    https://cloud.google.com/monitoring/custom-metrics/creating-metrics#custom-metric-resources
    for supported types
    Args:
            resource: OTel resource
    """

    attrs = resource.attributes

    platform = attrs.get(ResourceAttributes.CLOUD_PLATFORM_KEY)
    if platform == ResourceAttributes.GCP_COMPUTE_ENGINE:
        mr = _create_monitored_resource(GCE_INSTANCE, attrs)
    elif platform == ResourceAttributes.GCP_KUBERNETES_ENGINE:
        if ResourceAttributes.K8S_CONTAINER_NAME in attrs:
            mr = _create_monitored_resource(K8S_CONTAINER, attrs)
        elif ResourceAttributes.K8S_POD_NAME in attrs:
            mr = _create_monitored_resource(K8S_POD, attrs)
        elif ResourceAttributes.K8S_NODE_NAME in attrs:
            mr = _create_monitored_resource(K8S_NODE, attrs)
        else:
            mr = _create_monitored_resource(K8S_CLUSTER, attrs)
    elif platform == ResourceAttributes.AWS_EC2:
        mr = _create_monitored_resource(AWS_EC2_INSTANCE, attrs)
    else:
        # fallback to generic_task
        if (
            ResourceAttributes.SERVICE_NAME in attrs
            and ResourceAttributes.SERVICE_INSTANCE_ID in attrs
        ):
            mr = _create_monitored_resource(GENERIC_TASK, attrs)
        else:
            mr = _create_monitored_resource(GENERIC_NODE, attrs)

    return mr


def _create_monitored_resource(
    monitored_resource_type: str, resource_attrs: Attributes
) -> MonitoredResource:
    mapping = MAPPINGS[monitored_resource_type]
    labels: Dict[str, str] = {}

    for mr_key, map_config in mapping.items():
        mr_value = None
        for otel_key in map_config.otel_keys:
            if otel_key in resource_attrs:
                mr_value = resource_attrs[otel_key]
                break

        if mr_value is None:
            mr_value = map_config.fallback

        if not isinstance(mr_value, str):
            mr_value = json.dumps(
                mr_value, sort_keys=True, indent=None, separators=(",", ":")
            )
        labels[mr_key] = mr_value

    return MonitoredResource(type=monitored_resource_type, labels=labels)
