import unittest
import time
import os
import shutil
import tempfile
import socket
import subprocess
import sys

import requests

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


def _wait_for_mock_server(base_url: str, process: subprocess.Popen, timeout_s: float = 30.0) -> tuple[bool, str]:
    """Poll the mock server until it answers /reset or we run out of time."""
    deadline = time.monotonic() + timeout_s
    last_error = ""
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return False, last_error or f"mock server exited with code {process.returncode}"
        try:
            response = requests.post(
                f"{base_url}/reset",
                json={"scenarioType": "default", "useThinking": False},
                timeout=1,
            )
            if response.ok:
                return True, ""
            last_error = f"reset returned {response.status_code}: {response.text}"
        except requests.exceptions.RequestException as exc:
            last_error = str(exc)
        time.sleep(0.25)
    return False, last_error or "timed out waiting for mock server"


class _MockServerTestCaseBase(unittest.TestCase):
    """Base class for tests requiring a mock OpenAI server."""
    server_process: subprocess.Popen | None = None
    temp_dir: str | None = None
    mock_server_port: int | None = None
    mock_server_log_path: str | None = None

    @classmethod
    def setUpClass(cls):
        # Pick a free port per process to allow safe parallel test execution.
        # Under xdist, many workers may bind ports at once, so retry a few times
        # if a chosen port is stolen before uvicorn binds it.
        cls.temp_dir = tempfile.mkdtemp(prefix="test_llm_chess_integration_")
        cls.mock_server_log_path = os.path.join(cls.temp_dir, "mock_openai_server.log")
        last_error = ""
        for _ in range(5):
            cls.mock_server_port = _find_free_port()
            base_url = f"http://127.0.0.1:{cls.mock_server_port}/v1"

            # Start mock OpenAI server in a separate subprocess on the chosen port.
            # Using subprocess avoids multiprocessing restrictions in parallel test workers.
            with open(cls.mock_server_log_path, "w", encoding="utf-8") as log_file:
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
                    stdout=log_file,
                    stderr=log_file,
                )

            ready, last_error = _wait_for_mock_server(base_url, cls.server_process)
            if ready:
                # Export for tests and LLM config only after the server is actually live.
                os.environ["MOCK_BASE_URL"] = base_url
                os.environ["LOCAL_BASE_URL_W"] = base_url
                os.environ["LOCAL_BASE_URL_B"] = base_url
                return

            if cls.server_process and cls.server_process.poll() is None:
                try:
                    cls.server_process.terminate()
                    cls.server_process.wait(timeout=5)
                except Exception:
                    try:
                        cls.server_process.kill()
                    except Exception:
                        pass

        log_excerpt = ""
        if cls.mock_server_log_path and os.path.exists(cls.mock_server_log_path):
            with open(cls.mock_server_log_path, "r", encoding="utf-8", errors="replace") as log_file:
                log_excerpt = log_file.read()[-4000:]
        raise RuntimeError(f"Failed to start mock server after retries: {last_error}\n{log_excerpt}")

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

        if cls.temp_dir and os.path.exists(cls.temp_dir):  # Keep basic check if dir exists
            shutil.rmtree(cls.temp_dir, ignore_errors=True)
        cls.temp_dir = None  # Ensure temp_dir is reset
        cls.mock_server_log_path = None
