import os
import subprocess
import threading
import logging
import time
import psutil
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Callable
from pathlib import Path

# --- Configuration & State Types ---

class ProcessState(Enum):
    """Enumeration of possible process lifecycle states."""
    IDLE = auto()
    STARTING = auto()
    RUNNING = auto()
    STOPPING = auto()
    STOPPED = auto()
    FAILED = auto()
    CRASHED = auto()

@dataclass(frozen=True)
class ProcessConfig:
    """Immutable configuration for a managed process."""
    name: str
    executable_path: Path
    args: List[str] = field(default_factory=list)
    tags: Set[str] = field(default_factory=set)
    dependencies: List[str] = field(default_factory=list)
    auto_restart: bool = True
    working_dir: Optional[Path] = None

# --- Managed Process Implementation ---

class ManagedProcess:
    """
    Encapsulates the lifecycle and health monitoring of a single OS process.
    """
    def __init__(self, config: ProcessConfig):
        self.config = config
        self.state = ProcessState.IDLE
        self._proc_handle: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self.logger = logging.getLogger(f"Process.{config.name}")
        
        # Ensure log directory exists if needed
        self.log_file = Path(f"logs/{config.name}.log")
        self.log_file.parent.mkdir(exist_ok=True)

    def spawn(self) -> bool:
        """Attempts to start the process with thread-safe state transition."""
        with self._lock:
            if self.state == ProcessState.RUNNING:
                self.logger.info("Process already running.")
                return True

            self.state = ProcessState.STARTING
            try:
                # Prepare command
                cmd = [str(self.config.executable_path)] + self.config.args
                
                # Open log file for output redirection
                log_fh = open(self.log_file, "a")
                
                self._proc_handle = subprocess.Popen(
                    cmd,
                    cwd=self.config.working_dir,
                    stdout=log_fh,
                    stderr=subprocess.STDOUT,
                    text=True,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
                )
                
                self.state = ProcessState.RUNNING
                self.logger.info(f"Successfully spawned (PID: {self._proc_handle.pid})")
                return True
            except Exception as e:
                self.state = ProcessState.FAILED
                self.logger.error(f"Failed to spawn process: {str(e)}")
                return False

    def terminate(self, timeout: float = 10.0) -> bool:
        """Gracefully terminates then kills the process if it persists."""
        with self._lock:
            if not self._proc_handle or self.state in [ProcessState.STOPPED, ProcessState.IDLE]:
                return True

            self.state = ProcessState.STOPPING
            try:
                self._proc_handle.terminate()
                try:
                    self._proc_handle.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    self.logger.warning("Graceful termination timed out. Escalating to kill.")
                    self._proc_handle.kill()
                    self._proc_handle.wait()
                
                self.state = ProcessState.STOPPED
                self.logger.info("Process stopped.")
                return True
            except Exception as e:
                self.logger.error(f"Error during termination: {e}")
                return False

    def poll_health(self) -> ProcessState:
        """Checks the current OS status of the process and updates internal state."""
        with self._lock:
            if self.state != ProcessState.RUNNING:
                return self.state

            exit_code = self._proc_handle.poll()
            if exit_code is not None:
                if exit_code == 0:
                    self.state = ProcessState.STOPPED
                else:
                    self.state = ProcessState.CRASHED
                    self.logger.error(f"Detected crash. Exit code: {exit_code}")
            
            return self.state

    def get_metrics(self) -> Dict:
        """Retrieves resource usage metrics using psutil."""
        if self.state != ProcessState.RUNNING or not self._proc_handle:
            return {"cpu_percent": 0.0, "memory_mb": 0.0}
        
        try:
            p = psutil.Process(self._proc_handle.pid)
            return {
                "cpu_percent": p.cpu_percent(interval=0.1),
                "memory_mb": p.memory_info().rss / (1024 * 1024)
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return {"cpu_percent": 0.0, "memory_mb": 0.0}

# --- Orchestrator Implementation ---

class ProcessOrchestrator:
    """
    High-level manager for coordinating multiple processes and their dependencies.
    """
    def __init__(self):
        self._registry: Dict[str, ManagedProcess] = {}
        self._global_lock = threading.RLock() # Recursive lock for nested dependency starts
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s | %(name)-15s | %(levelname)-8s | %(message)s'
        )
        self.logger = logging.getLogger("Orchestrator")

    def register(self, config: ProcessConfig):
        """Adds a process configuration to the managed registry."""
        with self._global_lock:
            if config.name in self._registry:
                self.logger.warning(f"Overwriting existing process: {config.name}")
            self._registry[config.name] = ManagedProcess(config)

    def _start_recursive(self, name: str, visited: Set[str]):
        """Internal method to resolve and start dependencies using DFS."""
        if name in visited:
            raise RuntimeError(f"Circular dependency detected: {' -> '.join(visited)} -> {name}")
        
        visited.add(name)
        process = self._registry.get(name)
        
        if not process:
            self.logger.error(f"Dependency '{name}' not found in registry.")
            return

        # 1. Resolve dependencies first
        for dep_name in process.config.dependencies:
            self._start_recursive(dep_name, visited.copy())

        # 2. Start this process
        process.spawn()

    def start_process(self, name: str):
        """Public interface to start a process and its dependency tree."""
        with self._global_lock:
            try:
                self._start_recursive(name, set())
            except Exception as e:
                self.logger.error(f"Aborting start of {name}: {e}")

    def stop_all(self):
        """Gracefully shuts down all managed processes."""
        with self._global_lock:
            self.logger.info("Initiating global shutdown...")
            for proc in self._registry.values():
                proc.terminate()

    def run_health_monitor(self, interval: float = 2.0):
        """Starts a background thread for continuous health monitoring."""
        def monitor_task():
            while not self._stop_event.is_set():
                with self._global_lock:
                    for name, proc in self._registry.items():
                        current_state = proc.poll_health()
                        
                        if current_state == ProcessState.CRASHED and proc.config.auto_restart:
                            self.logger.info(f"Auto-restarting crashed process: {name}")
                            self.start_process(name)
                
                self._stop_event.wait(interval)

        self._monitor_thread = threading.Thread(target=monitor_task, daemon=True)
        self._monitor_thread.start()
        self.logger.info("Health monitor active.")

    def shutdown_orchestrator(self):
        """Full cleanup of the orchestrator and all children."""
        self._stop_event.set()
        self.stop_all()
        if self._monitor_thread:
            self._monitor_thread.join()
        self.logger.info("Orchestrator offline.")

# --- Example Usage ---

if __name__ == "__main__":
    # Standard engineering practice: wrap execution in entry point
    orchestrator = ProcessOrchestrator()
    
    # 1. Define configurations
    # Note: Using placeholders since specific paths vary by system
    config_a = ProcessConfig(
        name="BackendService",
        executable_path=Path("python.exe"),
        args=["-m", "http.server", "8080"],
        auto_restart=True
    )
    
    config_b = ProcessConfig(
        name="DataProcessor",
        executable_path=Path("python.exe"),
        args=["-c", "import time; print('Working...'); time.sleep(10)"],
        dependencies=["BackendService"],
        auto_restart=False
    )

    # 2. Register and Start
    orchestrator.register(config_a)
    orchestrator.register(config_b)
    
    orchestrator.run_health_monitor()
    
    # Starting DataProcessor will automatically start BackendService first
    orchestrator.start_process("DataProcessor")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        orchestrator.shutdown_orchestrator()

