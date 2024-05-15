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

from random import randint, uniform
import time
import logging
import requests
from flask import Flask, url_for
import setup_opentelemetry
import gcp_logging

from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.flask import FlaskInstrumentor

# [START opentelemetry_instrumentation_main]
logger = logging.getLogger(__name__)

app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()
# [END opentelemetry_instrumentation_main]

# [START opentelemetry_instrumentation_handle_multi]
@app.route('/multi')
def multi():
    subRequests = randint(3, 7)
    logger.info("handle /multi request", extra={'subRequests': subRequests})
    for _ in range(subRequests):
        requests.get(url_for('single', _external=True))
    return 'ok'
# [END opentelemetry_instrumentation_handle_multi]

# [START opentelemetry_instrumentation_handle_single]
@app.route('/single')
def single():
    duration = uniform(0.1, 0.2)
    time.sleep(duration)
    return f'slept {duration} seconds'
# [END opentelemetry_instrumentation_handle_single]
