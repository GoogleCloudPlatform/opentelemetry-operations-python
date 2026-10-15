#!./run_with_env.sh
import unittest

import sys
sys.path.append('../src')

from opentelemetry.configurator.gcp import OpenTelemetryGcpConfigurator

class ManualTestWithAllOptionsEnabled(unittest.TestCase):

    def test_does_not_crash(self):
        configurator = OpenTelemetryGcpConfigurator(
            metrics_exporter_enabled=True,
            logs_exporter_enabled=True,
            traces_exporter_enabled=True,
            resource_detector_enabled=True,
        )
        configurator.configure()


if __name__ == '__main__':
    unittest.main()
