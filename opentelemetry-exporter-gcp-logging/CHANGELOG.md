# Changelog

## Unreleased

## Version 1.11.0a0

Released 2025-11-04

## Version 1.10.0a0

Released 2025-10-13

- Added support for when a `Mapping[str, bytes]` or `Mapping[str, List[bytes]]` is in `LogRecord.body` or `LogRecord.attributes`.
- Added support for when a `Mapping[str, List[Mapping]]` is in `LogRecord.body` or `LogRecord.attributes`.
- Do not call `logging.warning` when `LogRecord.body` is of None type, instead leave `LogEntry.payload` empty.
- Update opentelemetry-api/sdk dependencies to 1.3.

The suffix part of `LogEntry.log_name` will be the `LogRecord.event_name` when
that is present and the `gcp.log_name` attribute is not.

## Version 1.9.0a0

Released 2025-02-03
