"""Open Telemetry configurator for Google Cloud

This package provides the 'OpenTelemetryGcpConfigurator' which simplifies configuration of the
Open Telemetry library to route logs, traces, and metrics to Google Cloud Observability products
such as Cloud Logging, Cloud Trace, and Cloud Monitoring.

The OpenTelemetryGcpConfigurator can be invoked directly as in:

    from opentelemetry.configurator.gcp import OpenTelemetryGcpConfigurator

    OpenTelemetryGcpConfigurator().configure()

It can also be invoked automatically from the "opentelemetry-instrument" command,
which is part of the Open Telemetry zero-code instrumentation for Python. To
invoke it automatically, simply supply "--configurator=gcp" as a commandline
flag to the "opentelemetry-instrument" command. As an example:

    opentelemetry-instrument \
        --configurator=gcp \
        python \
        the/path/to/your/script.py

This automatic wiring is implemented using the registration mechanism in "pyproject.toml";
in particular, the "[project.entry-points.opentelemetry_configurator]" entry in that file
makes this component known to the auto-instrumentation system. And it being a class
that defines a "configure(self, **kwargs)" method makes it compatible with that API.
."""

from .configurator import OpenTelemetryGcpConfigurator
from .version import __version__

__all__ = [
    "OpenTelemetryGcpConfigurator",
    "__version__",
]
