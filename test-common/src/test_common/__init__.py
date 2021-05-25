# Copyright 2021 Google LLC
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

"""Test utilities used across packages

This code is only used in other modules' tests
"""


from .base_exporter_integration_test import BaseExporterIntegrationTest

try:
    from time import time_ns as _time_ns
except ImportError:
    from time import time

    def _time_ns() -> int:
        return int(time() * 1e9)


def time_ns() -> int:
    """
    Use time.time_ns if it is available or convert time.time() to nanoseconds
    (lower resolution)

    TODO: remove when python3.6 is dropped
    """
    return _time_ns()


__all__ = ["time_ns", "BaseExporterIntegrationTest"]

