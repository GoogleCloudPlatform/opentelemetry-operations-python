#!/usr/bin/env python3
# Copyright 2025 Google LLC
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

import time

import google.auth
import google.auth.transport.grpc
import google.auth.transport.requests
import grpc
from google.auth.transport.grpc import AuthMetadataPlugin
from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
    OTLPMetricExporter,
)
from opentelemetry.resourcedetector.gcp_resource_detector import GoogleCloudResourceDetector
from opentelemetry.sdk.resources import SERVICE_NAME, Resource, get_aggregated_resources
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

"""
This is a sample script that exports OTLP metrics encoded as protobufs via gRPC. 
"""

credentials, project_id = google.auth.default()
request = google.auth.transport.requests.Request()
resource = get_aggregated_resources(
    [GoogleCloudResourceDetector(raise_on_error=True)]
)

auth_metadata_plugin = AuthMetadataPlugin(
    credentials=credentials, request=request
)
channel_creds = grpc.composite_channel_credentials(
    grpc.ssl_channel_credentials(),
    grpc.metadata_call_credentials(auth_metadata_plugin),
)

exporter = OTLPMetricExporter(credentials=channel_creds)
reader = PeriodicExportingMetricReader(exporter)
provider = MeterProvider(metric_readers=[reader],resource=resource)
meter = provider.get_meter("gcp.otlp.sample")
counter = meter.create_counter("sample.otlp.counter")


def do_work():
    counter.add(1)
    # do some work that the 'counter' will track
    print("doing some work...")


def do_work_repeatedly():
    try:
        while True:
            do_work()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nKeyboard Interrupt: Stopping work.")


do_work_repeatedly()
