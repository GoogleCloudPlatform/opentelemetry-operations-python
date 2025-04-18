# Copyright 2024 Google LLC
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

import logging
import time
from random import randint, uniform

import requests
from flask import Flask, url_for
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

from gcp_logging import setup_structured_logging
from setup_opentelemetry import setup_opentelemetry

# [START opentelemetry_instrumentation_main]
logger = logging.getLogger(__name__)

# Initialize OpenTelemetry Python SDK and structured logging
setup_opentelemetry()
setup_structured_logging()

app = Flask(__name__)

# Add instrumentation
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()
# [END opentelemetry_instrumentation_main]


# [START opentelemetry_instrumentation_handle_multi]
@app.route("/multi")
def multi():
    """Handle an http request by making 3-7 http requests to the /single endpoint."""
    sub_requests = randint(3, 7)
    logger.info("handle /multi request", extra={"subRequests": sub_requests})
    for _ in range(sub_requests):
        requests.get(url_for("single", _external=True))
    return "ok"


# [END opentelemetry_instrumentation_handle_multi]


# [START opentelemetry_instrumentation_handle_single]
@app.route("/single")
def single():
    """Handle an http request by sleeping for 100-200 ms, and write the number of seconds slept as the response."""
    duration = uniform(0.1, 0.2)
    time.sleep(duration)
    return f"slept {duration} seconds"


# [END opentelemetry_instrumentation_handle_single]
