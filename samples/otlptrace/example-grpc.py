#!/usr/bin/env python3
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

import google.auth
import google.auth.transport.grpc
import google.auth.transport.requests
from google.auth.transport.grpc import AuthMetadataPlugin
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
import grpc
import logging
import time

"""
This is a sample script that exports OTLP traces encoded as protobufs via gRPC. 
"""
logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.DEBUG,
    datefmt="%Y-%m-%d %H:%M:%S",
)

class AutoRefreshAuthMetadataPlugin(AuthMetadataPlugin):
    """
    A `gRPC AuthMetadataPlugin`_ that refreshes credentials and inserts them into
    each request.
    """
    def __init__(self, credentials, request, default_host=None):
        super().__init__(credentials, request, default_host)

    def __call__(self, context, callback):
        logging.info("Inserting credentials")
        if self._credentials.expired:
            logging.info("credentials expired, refresing")
            self._credentials.refresh(self._request)

        auth_headers = [("authorization", f"Bearer {self._credentials.token}")]
        logging.info(f"Adding headers {auth_headers}")
        callback(auth_headers, None)

credentials, project_id = google.auth.default()
request = google.auth.transport.requests.Request()
credentials.refresh(request)
resource = Resource.create(attributes={
    SERVICE_NAME: "otlp-gcp-grpc-sample"
})

auth_metadata_plugin = AutoRefreshAuthMetadataPlugin(credentials=credentials, request=request)
channel_creds = grpc.composite_channel_credentials(grpc.ssl_channel_credentials(),
                                                   grpc.metadata_call_credentials(auth_metadata_plugin))

logging.info("Channel creds %s", channel_creds._credentials)

trace_provider = TracerProvider(resource=resource)
processor = BatchSpanProcessor(OTLPSpanExporter(credentials=channel_creds, insecure=False, headers={
    "x-goog-user-project": credentials.quota_project_id,
}))
trace_provider.add_span_processor(processor)
trace.set_tracer_provider(trace_provider)
tracer = trace.get_tracer("my.tracer.name")

def do_work():
    with tracer.start_as_current_span("span-name") as span:
        # do some work that 'span' will track
        print("doing some work...")
        # When the 'with' block goes out of scope, 'span' is closed for you

def do_work_repeatedly():
    try:
        while True:
            do_work()
            time.sleep(10)
    except KeyboardInterrupt:
        print("\nKeyboard Interrupt: Stopping work.")

do_work_repeatedly()
