"""Provides a mechanism to configure the Resource Detector for GCP."""
from opentelemetry.sdk import resources as otel_resources_sdk
from opentelemetry.resourcedetector import gcp_resource_detector


def get_resource(include_gcp_detector=False):
    """Calculate the resource to use in Open Telemetry signals.
  
    Args:
      include_gcp_detector: Whether to merge in information about
        the GCP environment in which the code is running.

    Effects:
      Gathers information about the current environment to produce
      a resource that summarizes the running environment.

    Returns:
      A resource that summarizes the environment.
    """
    detectors = [
        otel_resources_sdk.OTELResourceDetector(),
        otel_resources_sdk.ProcessResourceDetector(),
        otel_resources_sdk.OsResourceDetector(),
    ]
    if include_gcp_detector:
        detectors.append(gcp_resource_detector.GoogleCloudResourceDetector())
    return otel_resources_sdk.get_aggregated_resources(detectors)
