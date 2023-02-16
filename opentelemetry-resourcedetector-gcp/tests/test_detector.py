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

from unittest.mock import Mock

import pytest
import requests
from opentelemetry.resourcedetector.gcp_resource_detector import _metadata
from opentelemetry.resourcedetector.gcp_resource_detector._detector import (
    GoogleCloudResourceDetector,
)


@pytest.fixture(autouse=True)
def fixture_reset_cache():
    yield
    _metadata.get_metadata.cache_clear()
    _metadata.is_available.cache_clear()


@pytest.fixture(name="fake_get", autouse=True)
def fixture_fake_get(monkeypatch: pytest.MonkeyPatch):
    mock = Mock()
    monkeypatch.setattr(requests, "get", mock)
    return mock


@pytest.fixture(name="fake_metadata", autouse=True)
def fixture_fake_metadata(fake_get: Mock):
    json = {"instance": {}, "project": {}}
    fake_get().json.return_value = json
    return json


def test_detects_empty_when_not_available(snapshot, fake_get: Mock):
    fake_get.side_effect = requests.HTTPError()
    assert dict(GoogleCloudResourceDetector().detect().attributes) == snapshot


def test_detects_empty_as_fallback(snapshot):
    assert dict(GoogleCloudResourceDetector().detect().attributes) == snapshot


def test_detects_gce(snapshot, fake_metadata: _metadata.Metadata):
    fake_metadata.update(
        {
            "project": {"projectId": "fakeProject"},
            "instance": {
                "name": "fakeName",
                "id": "fakeId",
                "machineType": "fakeMachineType",
                "zone": "projects/233510669999/zones/us-east4-b",
            },
        }
    )

    assert dict(GoogleCloudResourceDetector().detect().attributes) == snapshot
