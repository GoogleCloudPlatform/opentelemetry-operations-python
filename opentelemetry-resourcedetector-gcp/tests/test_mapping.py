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

import dataclasses

import pytest
from opentelemetry.resourcedetector.gcp_resource_detector._mapping import (
    get_monitored_resource,
)
from opentelemetry.sdk.resources import Attributes, LabelValue, Resource
from syrupy.assertion import SnapshotAssertion


@pytest.mark.parametrize(
    ("otel_attributes", "expected_type", "expected_labels"),
    [
        pytest.param(
            {
                "cloud.platform": "aws_ec2",
                "cloud.region": "us-east-1",
                "k8s.cluster.name": "mycluster",
                "k8s.namespace.name": "myns",
                "k8s.pod.name": "mypod",
                "k8s.container.name": "mycontainer",
            },
            "k8s_container",
            {
                "location": "us-east-1",
                "cluster_name": "mycluster",
                "namespace_name": "myns",
                "pod_name": "mypod",
                "container_name": "mycontainer",
            },
            id="container",
        ),
        pytest.param(
            {
                "cloud.platform": "aws_ec2",
                "cloud.region": "us-east-1",
                "k8s.cluster.name": "mycluster",
                "k8s.namespace.name": "myns",
                "k8s.pod.name": "mypod",
            },
            "k8s_pod",
            {
                "location": "us-east-1",
                "cluster_name": "mycluster",
                "namespace_name": "myns",
                "pod_name": "mypod",
            },
            id="pod",
        ),
        pytest.param(
            {
                "cloud.platform": "aws_ec2",
                "cloud.region": "us-east-1",
                "k8s.cluster.name": "mycluster",
                "k8s.node.name": "mynode",
            },
            "k8s_node",
            {
                "location": "us-east-1",
                "cluster_name": "mycluster",
                "node_name": "mynode",
            },
            id="node",
        ),
        pytest.param(
            {
                "cloud.platform": "aws_ec2",
                "cloud.region": "us-east-1",
                "k8s.cluster.name": "mycluster",
            },
            "k8s_cluster",
            {"location": "us-east-1", "cluster_name": "mycluster"},
            id="cluster",
        ),
    ],
)
def test_get_monitored_resource_non_gke_k8s(
    otel_attributes: Attributes,
    expected_type: str,
    expected_labels: dict[str, str],
) -> None:
    monitored_resource = get_monitored_resource(
        Resource.create(otel_attributes)
    )

    assert monitored_resource is not None
    assert monitored_resource.type == expected_type
    assert monitored_resource.labels == expected_labels


@pytest.mark.parametrize(
    "otel_attributes",
    [
        # GCE
        pytest.param(
            {
                "cloud.platform": "gcp_compute_engine",
                "cloud.availability_zone": "foo",
                "host.id": "myhost",
            },
            id="gce instance",
        ),
        # k8s container
        pytest.param(
            {
                "cloud.platform": "gcp_kubernetes_engine",
                "cloud.availability_zone": "myavailzone",
                "k8s.cluster.name": "mycluster",
                "k8s.namespace.name": "myns",
                "k8s.pod.name": "mypod",
                "k8s.container.name": "mycontainer",
            },
            id="k8s container",
        ),
        pytest.param(
            {
                "cloud.platform": "gcp_kubernetes_engine",
                "cloud.region": "myregion",
                "k8s.cluster.name": "mycluster",
                "k8s.namespace.name": "myns",
                "k8s.pod.name": "mypod",
                "k8s.container.name": "mycontainer",
            },
            id="k8s container region fallback",
        ),
        # k8s pod
        pytest.param(
            {
                "cloud.platform": "gcp_kubernetes_engine",
                "cloud.availability_zone": "myavailzone",
                "k8s.cluster.name": "mycluster",
                "k8s.namespace.name": "myns",
                "k8s.pod.name": "mypod",
            },
            id="k8s pod",
        ),
        pytest.param(
            {
                "cloud.platform": "gcp_kubernetes_engine",
                "cloud.region": "myregion",
                "k8s.cluster.name": "mycluster",
                "k8s.namespace.name": "myns",
                "k8s.pod.name": "mypod",
            },
            id="k8s pod region fallback",
        ),
        # k8s node
        pytest.param(
            {
                "cloud.platform": "gcp_kubernetes_engine",
                "cloud.availability_zone": "myavailzone",
                "k8s.cluster.name": "mycluster",
                "k8s.namespace.name": "myns",
                "k8s.node.name": "mynode",
            },
            id="k8s node",
        ),
        pytest.param(
            {
                "cloud.platform": "gcp_kubernetes_engine",
                "cloud.region": "myregion",
                "k8s.cluster.name": "mycluster",
                "k8s.namespace.name": "myns",
                "k8s.node.name": "mynode",
            },
            id="k8s node region fallback",
        ),
        # k8s cluster
        pytest.param(
            {
                "cloud.platform": "gcp_kubernetes_engine",
                "cloud.availability_zone": "myavailzone",
                "k8s.cluster.name": "mycluster",
                "k8s.namespace.name": "myns",
            },
            id="k8s cluster",
        ),
        pytest.param(
            {
                "cloud.platform": "gcp_kubernetes_engine",
                "cloud.region": "myregion",
                "k8s.cluster.name": "mycluster",
                "k8s.namespace.name": "myns",
            },
            id="k8s cluster region fallback",
        ),
        # aws ec2
        pytest.param(
            {
                "cloud.platform": "aws_ec2",
                "cloud.availability_zone": "myavailzone",
                "host.id": "myhostid",
                "cloud.account.id": "myawsaccount",
            },
            id="aws ec2",
        ),
        pytest.param(
            {
                "cloud.platform": "aws_ec2",
                "cloud.region": "myregion",
                "host.id": "myhostid",
                "cloud.account.id": "myawsaccount",
            },
            id="aws ec2 region fallback",
        ),
        # generic task
        pytest.param(
            {
                "cloud.availability_zone": "myavailzone",
                "service.namespace": "servicens",
                "service.name": "servicename",
                "service.instance.id": "serviceinstanceid",
            },
            id="generic task",
        ),
        pytest.param(
            {
                "cloud.region": "myregion",
                "service.namespace": "servicens",
                "service.name": "servicename",
                "service.instance.id": "serviceinstanceid",
            },
            id="generic task fallback region",
        ),
        pytest.param(
            {
                "service.namespace": "servicens",
                "service.name": "servicename",
                "service.instance.id": "serviceinstanceid",
            },
            id="generic task fallback global",
        ),
        pytest.param(
            {
                "service.name": "unknown_service",
                "cloud.region": "myregion",
                "service.namespace": "servicens",
                "faas.name": "faasname",
                "faas.instance": "faasinstance",
            },
            id="generic task faas",
        ),
        pytest.param(
            {
                "service.name": "unknown_service",
                "cloud.region": "myregion",
                "service.namespace": "servicens",
                "faas.instance": "faasinstance",
            },
            id="generic task faas fallback",
        ),
        # generic node
        pytest.param(
            {
                "cloud.availability_zone": "myavailzone",
                "service.namespace": "servicens",
                "service.name": "servicename",
                "host.id": "hostid",
            },
            id="generic node",
        ),
        pytest.param(
            {
                "cloud.region": "myregion",
                "service.namespace": "servicens",
                "service.name": "servicename",
                "host.id": "hostid",
            },
            id="generic node fallback region",
        ),
        pytest.param(
            {
                "service.namespace": "servicens",
                "service.name": "servicename",
                "host.id": "hostid",
            },
            id="generic node fallback global",
        ),
        pytest.param(
            {
                "service.namespace": "servicens",
                "service.name": "servicename",
                "host.name": "hostname",
            },
            id="generic node fallback host name",
        ),
        # fallback empty
        pytest.param(
            {"foo": "bar", "no.useful": "resourceattribs"},
            id="fallback generic node",
        ),
        pytest.param(
            {},
            id="empty",
        ),
    ],
)
def test_get_monitored_resource(
    otel_attributes: Attributes, snapshot: SnapshotAssertion
) -> None:
    resource = Resource(otel_attributes)
    monitored_resource_data = get_monitored_resource(resource)
    as_dict = dataclasses.asdict(monitored_resource_data)
    assert as_dict == snapshot


@pytest.mark.parametrize(
    ("value", "expect"),
    [
        (None, ""),
        (123, "123"),
        (123.4, "123.4"),
        ([1, 2, 3, 4], "[1,2,3,4]"),
        ([1.1, 2.2, 3.3, 4.4], "[1.1,2.2,3.3,4.4]"),
        (["a", "b", "c", "d"], '["a","b","c","d"]'),
    ],
)
def test_non_string_values(value: LabelValue, expect: str):
    # host.id will end up in generic_node's node_id label
    monitored_resource_data = get_monitored_resource(
        Resource({"host.id": value})
    )
    assert monitored_resource_data is not None

    value_as_gcm_label = monitored_resource_data.labels["node_id"]
    assert value_as_gcm_label == expect
