import unittest

from opentelemetry.google import constants


class TestConstants(unittest.TestCase):
    def test_nanos_is_seconds_is_int(self):
        self.assertIsInstance(constants.NANOS_PER_SECOND, int)
