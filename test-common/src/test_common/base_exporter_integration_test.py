import socket
import subprocess
import unittest


class BaseExporterIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.project_id = "TEST-PROJECT"

        # Find a free port to spin up our server at.
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("localhost", 0))
        self.address = "localhost:" + str(sock.getsockname()[1])
        sock.close()

        # Start the mock server.
        args = ["mock_server", "-address", self.address]
        self.mock_server_process = subprocess.Popen(
            args, stderr=subprocess.PIPE, stdout=subprocess.PIPE
        )
        # Block until the mock server starts (it will output the address after starting).
        if (
            self.mock_server_process.stderr is None
            or self.mock_server_process.stdout is None
        ):
            raise RuntimeError("stderr or stdout is None")
        self.mock_server_process.stderr.readline()

    def tearDown(self) -> None:
        self.mock_server_process.kill()
        if (
            self.mock_server_process.stderr is None
            or self.mock_server_process.stdout is None
        ):
            raise RuntimeError("stderr or stdout is None")
        stdout = self.mock_server_process.stdout.read().decode()
        stderr = self.mock_server_process.stderr.read().decode()
        if stderr or stdout:
            self.fail(
                "Mock server should not have had any output, got stdout:\n%s\n\nstderr:\n%s",
                stdout,
                stderr,
            )
