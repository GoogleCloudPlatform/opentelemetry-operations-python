# Copyright 2021 Google LLC
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

# Build relative to root of repository i.e. `docker build --file Dockerfile --tag=$tag ..`

FROM python:3.9-slim as python-base
ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    SRC="/src" 
WORKDIR $SRC

FROM python-base as build-base
# copy local dependencies
COPY opentelemetry-exporter-gcp-trace opentelemetry-exporter-gcp-trace
COPY opentelemetry-propagator-gcp opentelemetry-propagator-gcp
WORKDIR $SRC/e2e-test-server
# copy requirements/constraints
COPY e2e-test-server/requirements.txt e2e-test-server/constraints.txt ./
RUN python -m venv venv && ./venv/bin/pip install -r requirements.txt

FROM python-base
WORKDIR $SRC/e2e-test-server
COPY --from=build-base $SRC/e2e-test-server/venv venv/
COPY e2e-test-server/ ./

ENTRYPOINT ["./venv/bin/python", "main.py"]
