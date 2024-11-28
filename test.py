import unittest
import time
from unittest.mock import patch, MagicMock
from ExeProcessManager import *
from unittest.mock import patch
from subprocess import Popen, PIPE

class TestExeProcessManager(unittest.TestCase):

    def setUp(self):
        """Initialize the process manager before each test."""
        self.manager = ExeProcessManager()
        self.test_process = Process(
            path="./test.exe",  # Path to your executable
            name="test_process",
            idd="001",
        )
        self.manager.add_process(self.test_process)

    def test_add_process(self):
        """Test adding a process."""
        process = Process(path="./test.exe", name="new_process", idd="002")
        result = self.manager.add_process(process)
        self.assertTrue(result)
        self.assertIn("new_process", self.manager.processes)

    def test_get_process_by_name(self):
        """Test retrieving a process by name."""
        process = self.manager.get_process("test_process")
        self.assertEqual(process.name, "test_process")
        self.assertIsNotNone(process)

    def test_get_process_by_tag(self):
        """Test retrieving a process by tag."""
        self.test_process.tag = "test_tag"
        process = self.manager.get_process("test_tag")
        self.assertEqual(process.tag, "test_tag")
        self.assertIsNotNone(process)

    def test_start_process(self):
        """Test starting a process."""
        result = self.manager.start_process("test_process")
        self.assertTrue(result)
        self.assertTrue(self.test_process.is_running)

    def test_restart_process(self):
        """Test restarting a process."""
        # Start the process first
        self.manager.start_process("test_process")
        result = self.manager.restart_process("test_process")
        self.assertTrue(result)
        self.assertTrue(self.test_process.is_running)

    def test_stop_process(self):
        """Test stopping a process."""
        self.manager.start_process("test_process")
        result = self.manager.stop_process("test_process")
        self.assertTrue(result)
        self.assertFalse(self.test_process.is_running)

    @patch("psutil.Process")  # Mocking psutil for monitoring resource usage
    def test_get_resource_usage(self, mock_psutil):
        """Test fetching the resource usage."""
        mock_proc = mock_psutil.return_value
        mock_proc.cpu_percent.return_value = 50.0
        mock_proc.memory_info.return_value.rss = 104857600  # 100 MB

        # Start the process and check usage
        self.manager.start_process("test_process")
        usage = self.test_process.get_resource_usage()
        
        self.assertEqual(usage["cpu"], 50.0)
        self.assertEqual(usage["memory"], 100.0)

    def test_schedule_process(self):
        """Test scheduling a process to start."""
        self.manager.schedule_process("test_process", "start", "10:00")
        # This test won't execute the job, but should log the scheduling
        time.sleep(1)  # Give time for the scheduled job to trigger
        # Assert that the job is scheduled (check logs or internal state)
        # This part depends on your environment/logs

    def test_graceful_shutdown(self):
        """Test shutting down all processes gracefully."""
        self.manager.start_process("test_process")
        self.manager.graceful_shutdown(timeout=5)
        self.assertFalse(self.test_process.is_running)

    def test_view_logs(self):
        """Test viewing the logs of a process."""
        # This assumes the process has a log file, you may need to adjust the test to create one.
        log_content = self.manager.view_logs("test_process")
        self.assertIsNone(log_content)  # No logs for test_process in this test case

if __name__ == "__main__":
    unittest.main()