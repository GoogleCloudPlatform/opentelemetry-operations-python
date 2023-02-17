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

import os
from unittest.mock import MagicMock

import pytest
from opentelemetry.resourcedetector.gcp_resource_detector import _gke


# Reset stuff before every test
# pylint: disable=unused-argument
@pytest.fixture(autouse=True)
def autouse(fake_get_metadata, fake_environ):
    pass


def test_detects_on_gke() -> None:
    os.environ["KUBERNETES_SERVICE_HOST"] = "fakehost"
    assert _gke.on_gke()


def test_detects_not_on_gke() -> None:
    assert not _gke.on_gke()


def test_detects_host_id(fake_get_metadata: MagicMock) -> None:
    fake_get_metadata.return_value = {"instance": {"id": "fake"}}
    assert _gke.host_id() == "fake"


def test_detects_cluster_name(fake_get_metadata: MagicMock) -> None:
    fake_get_metadata.return_value = {
        "instance": {"attributes": {"cluster-name": "fake"}}
    }
    assert _gke.cluster_name() == "fake"


def test_detects_zone(fake_get_metadata: MagicMock) -> None:
    fake_get_metadata.return_value = {
        "instance": {"attributes": {"cluster-location": "us-east4-b"}}
    }
    zone_or_region = _gke.availability_zone_or_region()
    assert zone_or_region.type == "zone"
    assert zone_or_region.value == "us-east4-b"


def test_detects_region(fake_get_metadata: MagicMock) -> None:
    fake_get_metadata.return_value = {
        "instance": {"attributes": {"cluster-location": "us-east4"}}
    }
    zone_or_region = _gke.availability_zone_or_region()
    assert zone_or_region.type == "region"
    assert zone_or_region.value == "us-east4"


def test_throws_for_invalid_cluster_location(
    fake_get_metadata: MagicMock,
) -> None:
    fake_get_metadata.return_value = {
        "instance": {"attributes": {"cluster-location": "invalid"}}
    }

    with pytest.raises(
        Exception, match="unrecognized format for cluster location"
    ):
        _gke.availability_zone_or_region()
