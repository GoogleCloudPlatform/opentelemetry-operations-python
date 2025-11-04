# Changelog

## Unreleased

## Version 1.11.0

Released 2025-11-04

## Version 1.10.0

Released 2025-10-13

Update opentelemetry-api/sdk dependencies to 1.3.

## Version 1.9.0

Released 2025-02-03

## Version 1.8.0

Released 2025-01-08

## Version 1.7.0

Released 2024-08-27

- Add support for Python 3.12 (#343)
  ([#343](https://github.com/GoogleCloudPlatform/opentelemetry-operations-python/pull/343))

## Version 1.6.0

Released 2023-10-16

- Don't use `pkg_resources.get_distribution(..).version`
  ([#256](https://github.com/GoogleCloudPlatform/opentelemetry-operations-python/pull/256))

## Version 1.5.0

Released 2023-05-17

- Add support for Python 3.11
  ([#240](https://github.com/GoogleCloudPlatform/opentelemetry-operations-python/pull/240))

## Version 1.4.0

Released 2022-12-05

- Set gRPC user-agent when calling google APIs
  ([#216](https://github.com/GoogleCloudPlatform/opentelemetry-operations-python/pull/216))
- Drop support for Python 3.6, add 3.10
  ([#203](https://github.com/GoogleCloudPlatform/opentelemetry-operations-python/pull/203))

## Version 1.3.0

Released 2022-04-21

## Version 1.2.0

Released 2022-04-05

- Add entry point for Cloud Trace exporter to work with auto instrumentation
  ([#179](https://github.com/GoogleCloudPlatform/opentelemetry-operations-python/pull/179))

## Version 1.1.0

Released 2022-01-13

- Add optional resource attributes to trace spans with regex
  ([#145](https://github.com/GoogleCloudPlatform/opentelemetry-operations-python/pull/145))
- Upgrade `google-cloud-trace` dependency to version 1.1 or newer.
  ([#170](https://github.com/GoogleCloudPlatform/opentelemetry-operations-python/pull/170))
- Fix span attribute value truncation
  ([#173](https://github.com/GoogleCloudPlatform/opentelemetry-operations-python/pull/173))

## Version 1.0.0

Released 2021-05-13

## Version 1.0.0rc0

Released 2021-04-22

- Drop support for Python 3.5
  ([#123](https://github.com/GoogleCloudPlatform/opentelemetry-operations-python/pull/123))
- Split cloud trace and cloud monitoring exporters into separate packages
  ([#107](https://github.com/GoogleCloudPlatform/opentelemetry-operations-python/pull/107))
  ([#122](https://github.com/GoogleCloudPlatform/opentelemetry-operations-python/pull/122))

## Version 0.18b0

Released 2021-03-31

## Version 0.17b0

Released 2021-02-04

## Version 0.16b1

Released 2021-01-14

- Add mapping between opentelemetry and google traces attributes
  ([#90](https://github.com/GoogleCloudPlatform/opentelemetry-operations-python/pull/90))

## Version 0.15b0

Released 2020-11-04

## Version 0.14b0

Released 2020-10-27

- Fix breakages for opentelemetry-python v0.14b0
  ([#79](https://github.com/GoogleCloudPlatform/opentelemetry-operations-python/pull/79),
  [#83](https://github.com/GoogleCloudPlatform/opentelemetry-operations-python/pull/83))

## Version 0.13b0

Released 2020-09-17

## Version 0.12b0

Released 2020-08-17

- Add spankind support for trace exporter
  ([#58](https://github.com/GoogleCloudPlatform/opentelemetry-operations-python/pull/58))

## Version 0.11b0

Released 2020-08-05

- Add support for resources
  ([#853](https://github.com/open-telemetry/opentelemetry-python/pull/853))

## Version 0.10b0

Released 2020-06-23

- Add g.co/agent label for Google internal metrics tracking
  ([#833](https://github.com/open-telemetry/opentelemetry-python/pull/833))
- Adding trouble-shooting tips
  ([#827](https://github.com/open-telemetry/opentelemetry-python/pull/827))
- Added Cloud Trace context propagation
  ([#819](https://github.com/open-telemetry/opentelemetry-python/pull/819))
- Added tests to tox coverage files
  ([#804](https://github.com/open-telemetry/opentelemetry-python/pull/804))
- Add ability for exporter to add unique identifier
  ([#841](https://github.com/open-telemetry/opentelemetry-python/pull/841))
- Added tests to tox coverage files
  ([#804](https://github.com/open-telemetry/opentelemetry-python/pull/804))

## 0.9b0

Released 2020-06-10

- Initial release
