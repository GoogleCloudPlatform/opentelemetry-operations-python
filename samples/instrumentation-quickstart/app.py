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
from flask import Flask, url_for
import requests
import time

app = Flask(__name__)

# TODO: change the logging format to conform to GCP requirements
# TODO: Add manual metric instrumentation
# TODO: Add manual trace instrumentation

@app.route('/multi')
def multi():
    # TODO: add info log line here
    for _ in range(randint(3, 7)):
        requests.get(url_for('single', _external=True))
    return 'ok'

@app.route('/single')
def single():
    duration = uniform(0.1, 0.2)
    time.sleep(duration)
    return f'slept {duration} seconds'
