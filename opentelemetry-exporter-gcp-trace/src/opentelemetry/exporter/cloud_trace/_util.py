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

import os
import re
from contextlib import contextmanager
from os.path import abspath, dirname, pathsep
from typing import Generator


@contextmanager
def without_autoinstrumentation() -> Generator[None, None, None]:
    """Prevent auto instrumentation loop in any invoked subprocesses"""
    try:
        from opentelemetry.instrumentation.auto_instrumentation import (
            __file__ as autoinstrumentation_init_file,
        )

        if not autoinstrumentation_init_file:
            raise ImportError
    except ImportError:
        yield
        return

    orig = os.environ.get("PYTHONPATH")
    try:
        os.environ["PYTHONPATH"] = re.sub(
            rf"{dirname(abspath(autoinstrumentation_init_file))}{pathsep}?",
            "",
            os.environ["PYTHONPATH"],
        )
        yield
    finally:
        os.environ["PYTHONPATH"] = orig
