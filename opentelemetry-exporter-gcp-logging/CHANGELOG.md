# Changelog

## Unreleased

Added support for when `bytes` or `list['bytes']` is in `LogRecord.body` and
body is of type Mapping. Update opentelemetry-api/sdk dependencies to 1.3.

The suffix part of `LogEntry.log_name` will be the `LogRecord.event_name` when
that is present and the `gcp.log_name` attribute is not.

## Version 1.9.0a0

Released 2025-02-03
