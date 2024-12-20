import os
import subprocess
import time
import logging
import threading
import psutil
import schedule

# Initialize logging
logging.basicConfig(
    filename="process_manager.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


class Process:
    def __init__(
        self,
        path=None,
        name=None,
        tag=None,
        idd=None,
        thread=None,
        schulRule=None,
        args=None,
        dependencies=None,
    ):
        """
        Represents a single process to be managed.
        :param path: Path to the .exe file or executable script.
        :param name: Name of the process.
        :param tag: Tag for categorization.
        :param idd: Unique identifier for the process.
        :param thread: Thread for handling the process.
        :param schulRule: Scheduling rules.
        :param args: Command-line arguments for the process.
        :param dependencies: List of dependent process names that must start before this one.
        """
        self.path = path
        self.name = name
        self.tag = tag
        self.idd = idd
        self.schulRule = schulRule
        self.args = args or []
        self.dependencies = dependencies or []
        self.process = None
        self.is_running = False
        self.thread = None

    def get_resource_usage(self):
        """Get CPU and memory usage of the process."""
        if not self.is_running or not self.process:
            return {"cpu": 0, "memory": 0}
        
        try:
            proc = psutil.Process(self.process.pid)
            # Check if the process is still alive
            if not proc.is_running() or proc.status() == psutil.STATUS_ZOMBIE:
                logging.warning(f"Process '{self.name}' with PID {self.process.pid} is no longer active.")
                self.is_running = False
                return {"cpu": 0, "memory": 0}

            # Retrieve resource usage
            return {
                "cpu": proc.cpu_percent(interval=0.1),  # Short interval for CPU usage
                "memory": proc.memory_info().rss / 1024**2,  # Memory in MB
            }
        except psutil.NoSuchProcess:
            # Process is no longer active
            logging.warning(f"Process '{self.name}' with PID {self.process.pid} no longer exists.")
            self.is_running = False
            return {"cpu": 0, "memory": 0}
        except Exception as e:
            # Handle other unexpected errors
            logging.error(f"Error fetching resource usage for '{self.name}': {e}")
            return {"cpu": 0, "memory": 0}

    def set_priority(self, priority):
        """Set the process priority."""
        if self.process and self.is_running:
            try:
                ps = psutil.Process(self.process.pid)
                ps.nice(priority)
                logging.info(f"Set priority for '{self.name}' to {priority}.")
            except psutil.NoSuchProcess:
                self.is_running = False
            except Exception as e:
                logging.error(f"Error setting priority for '{self.name}': {e}")


class ExeProcessManager:
    def __init__(self):
        self.processes = {}
        self.lock = threading.Lock()

    def add_process(self, process: Process):
        """Add a process to the manager."""
        with self.lock:
            if process.name in self.processes:
                logging.warning(f"Process '{process.name}' already exists.")
                return False
            self.processes[process.name] = process
            logging.info(f"Process '{process.name}' added successfully.")
            return True

    def get_process(self, identifier):
        """Retrieve a process by name, tag, or id."""
        with self.lock:
            for process in self.processes.values():
                if process.name == identifier or process.tag == identifier or process.idd == identifier:
                    return process
            logging.warning(f"No process found with identifier: {identifier}")
            return None  # Immediately return None if process is not found

    def start_process(self, identifier):
        """Start a specific process."""
        process = self.get_process(identifier)
        if not process:
            return False

        if not os.path.exists(process.path):
            logging.error(f"Executable '{process.path}' not found for process '{process.name}'.")
            return False

        if process.dependencies:
            for dep in process.dependencies:
                if not self.start_process(dep):
                    logging.error(f"Dependency '{dep}' failed to start.")
                    return False

        try:
            if process.is_running:
                logging.warning(f"Process '{process.name}' is already running.")
                return False

            # Correct handling for Windows
            args = [process.path] + process.args
            process.process = subprocess.Popen(args)  # Do not join args with space

            process.is_running = True
            logging.info(f"Started process '{process.name}'.")
            return True
        except Exception as e:
            logging.error(f"Error starting process '{process.name}': {e}")
            return False
   
    def restart_process(self, identifier):
        """Restart a specific process."""
        process = self.get_process(identifier)
        if not process:
            logging.error(f"Process '{identifier}' not found.")
            return False

        try:
            if process.is_running:
                logging.info(f"Stopping process '{process.name}' to restart...")
                self.stop_process(identifier)  # This will run asynchronously and raise an exception if failed
            else:
                logging.info(f"Process '{process.name}' is not running. Skipping stop step.")
            
            logging.info(f"Starting process '{process.name}' again...")
            if self.start_process(identifier):
                logging.info(f"Successfully restarted process '{process.name}'.")
                return True
            else:
                logging.error(f"Failed to restart process '{process.name}'.")
                return False
        except Exception as e:
            logging.error(f"Failed to restart process '{process.name}': {e}")
            return False
    
    def start_all(self):
        """Start all processes."""
        with self.lock:
            for process in self.processes.values():
                self.start_process(process.name)
    
    def stop_process(self, identifier):
        """Stop a specific process asynchronously."""
        def stop():
            process = self.get_process(identifier)

            if not process:
                logging.warning(f"Process '{identifier}' not found.")
                return False  # Return False if process is not found

            with self.lock:  # Lock access to the shared resource (process state)
                if not process.is_running:
                    logging.info(f"Process '{identifier}' is not running.")
                    return True  # Process is already not running, no need to stop

                try:
                    logging.info(f"Stopping process '{identifier}'...")
                    process.process.terminate()  # Attempt to gracefully stop
                    process.process.communicate()  # Ensure that we clean up the subprocess
                    process.is_running = False
                    logging.info(f"Successfully stopped process '{identifier}'.")
                    return True  # Successfully stopped
                except subprocess.TimeoutExpired:
                    logging.warning(f"Process '{identifier}' didn't stop in time, forcefully terminating.")
                    process.process.kill()  # Force kill if the process takes too long to stop
                    process.process.communicate()  # Clean up any remaining process
                    process.is_running = False
                    return False  # Return False if it couldn't stop within the timeout
                except Exception as e:
                    logging.error(f"Error stopping process '{identifier}': {e}")
                    return False  # Return False on error

        stop_thread = threading.Thread(target=stop, daemon=False)  # Change daemon=False to ensure cleanup
        stop_thread.start()

        # Wait for the background thread to complete before checking the result
        stop_thread.join()  # This ensures that we wait for the stop operation to complete
        process = self.get_process(identifier)

        if process and not process.is_running:
            logging.info(f"Process '{identifier}' has been successfully stopped.")
            return True  # Process is stopped successfully
        else:
            logging.error(f"Failed to stop process '{identifier}' or it is still running.")
            return False  # Failed to stop the process

    def restart_all(self):
        """Restart all processes."""
        with self.lock:
            for process in self.processes.values():
                self.restart_process(process.name)

    def start_group(self, tag):
        """Start all processes with the specified tag."""
        with self.lock:
            for process in self.processes.values():
                if process.tag == tag:
                    self.start_process(process.name)

    def stop_group(self, tag):
        """Stop all processes with the specified tag."""
        with self.lock:
            for process in self.processes.values():
                if process.tag == tag:
                    self.stop_process(process.name)

    def schedule_process(self, identifier, action, time_str):
        """Schedule a process to perform an action at a specific time."""
        process = self.get_process(identifier)
        if not process:
            return False

        def job():
            if action == "start":
                self.start_process(identifier)
            elif action == "stop":
                self.stop_process(identifier)
            elif action == "restart":
                self.restart_process(identifier)

        schedule.every().day.at(time_str).do(job)
        logging.info(f"Scheduled '{action}' for process '{identifier}' at {time_str}.")

    def monitor_processes(self, check_interval=5):
        """Monitor all processes and restart if needed."""
        while True:
            with self.lock:
                for process in self.processes.values():
                    if process.is_running and process.process.poll() is not None:
                        logging.warning(f"Process '{process.name}' stopped unexpectedly. Restarting...")
                        self.restart_process(process.name)
            time.sleep(check_interval)

    def graceful_shutdown(self, timeout=30):
        """Shut down all processes gracefully with a timeout."""
        try:
            start_time = time.time()
            for process in self.processes.values():
                self.stop_process(process.name)

            # Wait until all processes are stopped or timeout is reached
            while time.time() - start_time < timeout:
                all_stopped = all(not process.is_running for process in self.processes.values())
                if all_stopped:
                    break
                time.sleep(1)
            else:
                logging.warning("Timeout reached while waiting for processes to stop.")
            
            logging.info("All processes stopped.")
        except Exception as e:
            logging.error(f"Error during graceful shutdown: {e}")

    def view_logs(self, identifier):
        """View logs for a specific process."""
        process = self.get_process(identifier)
        if not process:
            return None
        log_file = f"{process.name}.log"
        try:
            with open(log_file, "r") as file:
                return file.read()
        except FileNotFoundError:
            logging.warning(f"Log file for '{process.name}' not found.")
            return None
