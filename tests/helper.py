import unittest
import time
import os
import shutil
import tempfile
import socket
import subprocess
import sys

def get_mock_base_url() -> str:
    """Return the mock server base URL for tests.

    Reads the dynamically assigned URL from the environment when available.
    Falls back to localhost:8080 for compatibility when run serially.
    """
    return os.environ.get("MOCK_BASE_URL", "http://127.0.0.1:8080/v1")


# Default environment for LLM configs points at the (possibly to-be-updated) base URL
_default_base = get_mock_base_url()

# White player settings
os.environ["MODEL_KIND_W"] = "local"
os.environ["LOCAL_MODEL_NAME_W"] = "gpt-3.5-turbo"
os.environ["LOCAL_BASE_URL_W"] = _default_base
os.environ["LOCAL_API_KEY_W"] = "mock-key"

# Black player settings
os.environ["MODEL_KIND_B"] = "local"
os.environ["LOCAL_MODEL_NAME_B"] = "gpt-3.5-turbo"
os.environ["LOCAL_BASE_URL_B"] = _default_base
os.environ["LOCAL_API_KEY_B"] = "mock-key"


def _find_free_port() -> int:
    """Find an available TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class _MockServerTestCaseBase(unittest.TestCase):
    """Base class for tests requiring a mock OpenAI server."""
    server_process: subprocess.Popen | None = None
    temp_dir: str | None = None
    mock_server_port: int | None = None

    @classmethod
    def setUpClass(cls):
        # Pick a free port per process to allow safe parallel test execution
        cls.mock_server_port = _find_free_port()
        base_url = f"http://127.0.0.1:{cls.mock_server_port}/v1"

        # Export for tests and LLM config
        os.environ["MOCK_BASE_URL"] = base_url
        os.environ["LOCAL_BASE_URL_W"] = base_url
        os.environ["LOCAL_BASE_URL_B"] = base_url

        # Start mock OpenAI server in a separate subprocess on the chosen port
        # Using subprocess avoids multiprocessing restrictions in parallel test workers
        cls.server_process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "tests.mock_openai_server:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(cls.mock_server_port),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(2)  # Wait for server to start
        cls.temp_dir = tempfile.mkdtemp(prefix="test_llm_chess_integration_")

    @classmethod
    def tearDownClass(cls):
        if cls.server_process and cls.server_process.poll() is None:  # Process still running
            try:
                cls.server_process.terminate()
                cls.server_process.wait(timeout=5)
            except Exception:
                try:
                    cls.server_process.kill()
                except Exception:
                    pass
            
        if cls.temp_dir and os.path.exists(cls.temp_dir): # Keep basic check if dir exists
            shutil.rmtree(cls.temp_dir, ignore_errors=True)
        cls.temp_dir = None # Ensure temp_dir is reset
