# Changelog

## Unreleased

## Version 1.11.0a0

Released 2025-11-04

## Version 1.10.0a0

Released 2025-10-13

- Update opentelemetry-api/sdk dependencies to 1.3.

- This is a breaking change which moves our official recource detector from `opentelemetry.resourcedetector.gcp_resource_detector._detector`
into `opentelemetry.resourcedetector.gcp_resource_detector` and deletes the outdated duplicate resource detector
which used to be there. Use `from opentelemetry.resourcedetector.gcp_resource_detector import GoogleCloudResourceDetector`
to import it. See ([#389](https://github.com/GoogleCloudPlatform/opentelemetry-operations-python/pull/389)) for details.

## Version 1.9.0a0

Released 2025-02-03

## Version 1.8.0a0

Released 2025-01-08

- Use a shorter connection timeout for reading metadata
  ([#362](https://github.com/GoogleCloudPlatform/opentelemetry-operations-python/pull/362))
- Fix creation of resources in _detector
  ([#366](https://github.com/GoogleCloudPlatform/opentelemetry-operations-python/pull/366))

## Version 1.7.0a0

Released 2024-08-27

- Implement GAE resource detection
  ([#351](https://github.com/GoogleCloudPlatform/opentelemetry-operations-python/pull/351))
- Implement Cloud Run and Cloud Functions faas resource detection
  ([#346](https://github.com/GoogleCloudPlatform/opentelemetry-operations-python/pull/346))
- Small fixups for resource detector code and tests
  ([#345](https://github.com/GoogleCloudPlatform/opentelemetry-operations-python/pull/345))
- gcp_resource_detector: add missing timeout to requests call
  ([#344](https://github.com/GoogleCloudPlatform/opentelemetry-operations-python/pull/344))
- Add support for Python 3.12 (#343)
  ([#343](https://github.com/GoogleCloudPlatform/opentelemetry-operations-python/pull/343))
- Don't throw and exception when raise on error is set to false
  ([#293](https://github.com/GoogleCloudPlatform/opentelemetry-operations-python/pull/293))

## Version 1.6.0a0

Released 2023-10-16

- Use faas.instance instead of faas.id, and bump e2e test image
  ([#271](https://github.com/GoogleCloudPlatform/opentelemetry-operations-python/pull/271))
- Map faas.* attributes to generic_task in resource mapping
  ([#273](https://github.com/GoogleCloudPlatform/opentelemetry-operations-python/pull/273))

## Version 1.5.0a0

Released 2023-05-17

- Add spec compliant GCE detection
  ([#231](https://github.com/GoogleCloudPlatform/opentelemetry-operations-python/pull/231))
- Add support for Python 3.11
  ([#240](https://github.com/GoogleCloudPlatform/opentelemetry-operations-python/pull/240))

## Version 1.4.0a0

Released 2022-12-05

- Drop support for Python 3.6, add 3.10
  ([#203](https://github.com/GoogleCloudPlatform/opentelemetry-operations-python/pull/203))
- Update no container name behaviour
  ([#186](https://github.com/GoogleCloudPlatform/opentelemetry-operations-python/pull/186))

## Version 1.3.0a0

Released 2022-04-21

- remove google-auth dependency for resource detection
  ([#176](https://github.com/GoogleCloudPlatform/opentelemetry-operations-python/pull/176))

## Version 1.2.0a0

Released 2022-04-05

## Version 1.1.0a0

Released 2022-01-13

## Version 1.0.0a0

Released 2021-04-22

- Drop support for Python 3.5
  ([#123](https://github.com/GoogleCloudPlatform/opentelemetry-operations-python/pull/123))
- Split tools package into separate propagator and resource detector packages
  ([#124](https://github.com/GoogleCloudPlatform/opentelemetry-operations-python/pull/124))

## Version 0.18b0

Released 2021-03-31

- Map span status code properly to GCT
  ([#113](https://github.com/GoogleCloudPlatform/opentelemetry-operations-python/pull/113))
- Handle mixed case cloud propagator headers
  ([#112](https://github.com/GoogleCloudPlatform/opentelemetry-operations-python/pull/112))

## Version 0.17b0

Released 2021-02-04

## Version 0.16b1

Released 2021-01-14

## Version 0.15b0

Released 2020-11-04

## Version 0.14b0

Released 2020-10-27

- Fix breakages for opentelemetry-python v0.14b0
  ([#79](https://github.com/GoogleCloudPlatform/opentelemetry-operations-python/pull/79))

## Version 0.13b0

Released 2020-09-17

## Version 0.12b0

Released 2020-08-17

## Version 0.11b0

Released 2020-08-05

- Add support for resources
  ([#853](https://github.com/open-telemetry/opentelemetry-python/pull/853))
