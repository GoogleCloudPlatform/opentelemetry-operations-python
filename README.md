# Open-Telemetry Operations Exporters for Python

[![Documentation Status](https://readthedocs.org/projects/google-cloud-opentelemetry/badge/?version=latest)](https://google-cloud-opentelemetry.readthedocs.io/en/latest/?badge=latest)
<!-- todo add pypi badges here -->

> [!WARNING]
> **DEPRECATION NOTICE**: This repository and all of its contents are deprecated and will be archived on October 30th, 2026. Please refer to the [Migration Guide](MIGRATION.md) for detailed instructions on migrating your application to standard OpenTelemetry OTLP exporters and W3C Trace Context propagation.

This repo provides OpenTelemetry Python exporters, propagators, and resource detectors
for Google Cloud Platform.

To get started with instrumentation in Google Cloud, see [Generate traces and metrics with
Python](https://cloud.google.com/stackdriver/docs/instrumentation/setup/python).

## Google Cloud Resource Detector

The OpenTelemetry Google Cloud Resource Detector (`opentelemetry-resourcedetector-gcp`) has moved to the [opentelemetry-python-contrib](https://github.com/open-telemetry/opentelemetry-python-contrib/tree/main/resource/opentelemetry-resourcedetector-gcp) repository:
https://github.com/open-telemetry/opentelemetry-python-contrib/tree/main/resource/opentelemetry-resourcedetector-gcp

## Documentation

To learn more about instrumentation and observability, including opinionated recommendations
for Google Cloud Observability, visit [Instrumentation and
observability](https://cloud.google.com/stackdriver/docs/instrumentation/overview).

API docs and additional examples are available at <https://google-cloud-opentelemetry.readthedocs.io/en/latest/>

## Installation

All packages are [available on PyPI](https://pypi.org/user/google_opentelemetry/) for installation with `pip`.

## Contributing

See the [contributing guide](docs/contributing.md).
