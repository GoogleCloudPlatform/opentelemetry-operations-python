#!./run_with_env.sh
import unittest

import sys
sys.path.append('../src')

from opentelemetry.configurator.gcp import OpenTelemetryGcpConfigurator

class ManualTestWithDefaultParameters(unittest.TestCase):

    def test_does_not_crash(self):
        OpenTelemetryGcpConfigurator().configure()


if __name__ == '__main__':
    unittest.main()
