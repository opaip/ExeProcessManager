import subprocess
import time
import os
import logging
import signal

class ExeProcessManager:
    def __init__(self, exe_path, log_file="process_manager.log"):
        self.exe_path = exe_path
        self.process = None
        self.is_running = False
        
        # Set up logging
        logging.basicConfig(
            filename=log_file, 
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.start_process()

    def start_process(self):
        """Start the .exe file and return the process."""
        try:
            if self.is_running:
                logging.warning("Process is already running.")
                return False

            self.process = subprocess.Popen(self.exe_path, shell=True)
            self.is_running = True
            logging.info(f"Started process: {self.exe_path}")
            return True
        except Exception as e:
            logging.error(f"Error starting {self.exe_path}: {e}")
            return False

    def stop_process(self):
        """Stop the currently running process."""
        try:
            if self.process and self.is_running:
                self.process.terminate()
                self.process.wait()
                self.is_running = False
                logging.info("Process terminated successfully.")
                return True
            else:
                logging.warning("No running process to stop.")
                return False
        except Exception as e:
            logging.error(f"Error stopping process: {e}")
            return False

    def restart_process(self):
        """Restart the .exe process."""
        if self.stop_process():
            time.sleep(1)  # Wait a moment before restarting
            return self.start_process()
        else:
            logging.error("Failed to restart process.")
            return False

    def auto_restart(self, check_interval=5):
        """Automatically restart the process if it stops unexpectedly."""
        try:
            while True:
                if not self.is_running:
                    logging.info("Process stopped unexpectedly. Restarting...")
                    self.start_process()
                
                time.sleep(check_interval)  # Check every 5 seconds
        except KeyboardInterrupt:
            logging.info("Auto-restart stopped manually.")
            self.stop_process()

    def monitor_process(self):
        """Monitor the process health."""
        try:
            if self.process and self.is_running:
                self.process.poll()  # Check if the process is still running
                if self.process.returncode is not None:
                    logging.warning("Process has terminated unexpectedly.")
                    self.is_running = False
                    return False
                return True
            else:
                logging.warning("Process is not running.")
                return False
        except Exception as e:
            logging.error(f"Error monitoring process: {e}")
            return False

    def graceful_shutdown(self):
        """Gracefully shut down the process manager."""
        try:
            logging.info("Shutting down the process manager...")
            if self.is_running:
                self.stop_process()
            logging.info("Shutdown complete.")
        except Exception as e:
            logging.error(f"Error during shutdown:{e}")


