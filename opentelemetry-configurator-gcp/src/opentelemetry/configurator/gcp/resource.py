from opentelemetry.sdk import resources as otel_resources_sdk
from opentelemetry.resourcedetector import gcp_resource_detector


def get_resource(include_gcp_detector=False):
  detectors = [
      otel_resources_sdk.OTELResourceDetector(),
      otel_resources_sdk.ProcessResourceDetector(),
      otel_resources_sdk.OsResourceDetector(),
  ]
  if include_gcp_detector:
      detectors.append(gcp_resource_detector.GoogleCloudResourceDetector())
  return otel_resources_sdk.get_aggregated_resources(detectors)
