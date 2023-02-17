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

from unittest.mock import MagicMock

import pytest
from opentelemetry.resourcedetector.gcp_resource_detector import (
    _gce,
    _metadata,
)


# Reset stuff before every test
# pylint: disable=unused-argument
@pytest.fixture(autouse=True)
def autouse(fake_get_metadata, fake_environ):
    pass


def test_detects_on_gce() -> None:
    assert _gce.on_gce()


def test_detects_not_on_gce(fake_get_metadata: MagicMock) -> None:
    # when the metadata server is not accessible
    fake_get_metadata.side_effect = _metadata.MetadataAccessException()
    assert not _gce.on_gce()

    # when the metadata server doesn't have the expected structure
    fake_get_metadata.return_value = {}
    assert not _gce.on_gce()


def test_detects_host_type(fake_get_metadata: MagicMock) -> None:
    fake_get_metadata.return_value = {"instance": {"machineType": "fake"}}
    assert _gce.host_type() == "fake"


def test_detects_host_id(fake_get_metadata: MagicMock) -> None:
    fake_get_metadata.return_value = {"instance": {"id": "fake"}}
    assert _gce.host_id() == "fake"


def test_detects_host_name(fake_get_metadata: MagicMock) -> None:
    fake_get_metadata.return_value = {"instance": {"name": "fake"}}
    assert _gce.host_name() == "fake"


def test_detects_zone_and_region(fake_get_metadata: MagicMock) -> None:
    fake_get_metadata.return_value = {
        "instance": {"zone": "projects/233510669999/zones/us-east4-b"}
    }
    zone_and_region = _gce.availability_zone_and_region()

    assert zone_and_region.zone == "us-east4-b"
    assert zone_and_region.region == "us-east4"


def test_throws_for_invalid_zone(fake_get_metadata: MagicMock) -> None:
    fake_get_metadata.return_value = {"instance": {"zone": ""}}

    with pytest.raises(Exception, match="zone was not in the expected format"):
        _gce.availability_zone_and_region()
