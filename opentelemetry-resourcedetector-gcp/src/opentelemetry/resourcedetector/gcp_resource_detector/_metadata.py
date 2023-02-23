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

import logging
from functools import lru_cache

import requests

# TODO: remove when Python 3.7 is dropped
from typing_extensions import TypedDict

_GCP_METADATA_URL = "http://metadata.google.internal/computeMetadata/v1/"
_INSTANCE = "instance"
_RECURSIVE_PARAMS = {"recursive": "true"}
_GCP_METADATA_URL_HEADER = {"Metadata-Flavor": "Google"}
_TIMEOUT_SEC = 5

_logger = logging.getLogger(__name__)


class Project(TypedDict):
    projectId: str


Attributes = TypedDict(
    "Attributes", {"cluster-location": str, "cluster-name": str}
)


class Instance(TypedDict):
    attributes: Attributes
    id: str
    machineType: str
    name: str
    zone: str


class Metadata(TypedDict):
    instance: Instance
    project: Project


class MetadataAccessException(Exception):
    pass


@lru_cache(maxsize=None)
def get_metadata() -> Metadata:
    """Get all instance and project metadata from the metadata server

    Cached for the lifetime of the process.
    """
    try:
        res = requests.get(
            f"{_GCP_METADATA_URL}",
            params=_RECURSIVE_PARAMS,
            headers=_GCP_METADATA_URL_HEADER,
            timeout=_TIMEOUT_SEC,
        )
        res.raise_for_status()
        all_metadata = res.json()
    except requests.RequestException as err:
        raise MetadataAccessException() from err
    return all_metadata


@lru_cache(maxsize=None)
def is_available() -> bool:
    try:
        requests.get(
            f"{_GCP_METADATA_URL}{_INSTANCE}/",
            headers=_GCP_METADATA_URL_HEADER,
            timeout=_TIMEOUT_SEC,
        ).raise_for_status()
    except requests.RequestException:
        _logger.debug(
            "Failed to make request to metadata server, assuming it's not available",
            exc_info=True,
        )
        return False
    return True
