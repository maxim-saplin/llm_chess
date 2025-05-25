import unittest
import multiprocessing
import time
import os
import shutil
import tempfile
from tests.mock_openai_server import start_server

# White player settings
os.environ["MODEL_KIND_W"] = "local"
os.environ["LOCAL_MODEL_NAME_W"] = "gpt-3.5-turbo"
os.environ["LOCAL_BASE_URL_W"] = "http://localhost:8080/v1"
os.environ["LOCAL_API_KEY_W"] = "mock-key"

# Black player settings
os.environ["MODEL_KIND_B"] = "local"
os.environ["LOCAL_MODEL_NAME_B"] = "gpt-3.5-turbo"
os.environ["LOCAL_BASE_URL_B"] = "http://localhost:8080/v1"
os.environ["LOCAL_API_KEY_B"] = "mock-key"


class _MockServerTestCaseBase(unittest.TestCase):
    """Base class for tests requiring a mock OpenAI server."""
    server_process: multiprocessing.Process | None = None
    temp_dir: str | None = None

    @classmethod
    def setUpClass(cls):
        # Start mock OpenAI server in a separate process
        cls.server_process = multiprocessing.Process(target=start_server, args=(8080,))
        cls.server_process.start()
        time.sleep(2)  # Wait for server to start
        cls.temp_dir = tempfile.mkdtemp(prefix="test_llm_chess_integration_")

    @classmethod
    def tearDownClass(cls):
        if cls.server_process and cls.server_process.is_alive(): # Keep basic check if process exists
            cls.server_process.terminate()
            cls.server_process.join()
            
        if cls.temp_dir and os.path.exists(cls.temp_dir): # Keep basic check if dir exists
            shutil.rmtree(cls.temp_dir, ignore_errors=True)
        cls.temp_dir = None # Ensure temp_dir is reset
