#!/usr/bin/env python3

import subprocess
import unittest

class AutomaticInstrumentationTestCase(unittest.TestCase):

    def test_works_with_auto_instrumentation(self):
        subprocess.run("./test_automatic.sh", shell=True, check=True, capture_output=True)


if __name__ == '__main__':
    unittest.main()
