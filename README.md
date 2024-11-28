# **Process Manager and Scheduler**

This project includes a **Process Manager** for managing system processes, and a **Scheduler** for scheduling operations like start, stop, and restart at specific times. This is useful for automating the management of long-running processes or tasks on your system.

---

## **Features**

- **Process Manager (`ExeProcessManager`)**: 
    - Start, stop, restart, and monitor processes.
    - Supports managing processes by name, tag, or dependencies.
    - Graceful shutdown and error handling.
    - Auto-restart for processes that stop unexpectedly.

- **Scheduler**:
    - Schedule actions like starting or stopping processes at specific times.
    - Supports recurring jobs or one-time execution.

---

## **Installation**

Clone the repository to your local machine:

```bash
git clone https://github.com/opaip/ExeProcessManager.git
```

Install the required dependencies (if any):
```bash
pip install -r requirements.txt
```

## **Usage**
**1. Using the `ExeProcessManager`**
You can use the ExeProcessManager class to manage processes on your system.
```python
from ExeProcessManager import ExeProcessManager, Process

# Create a process object
process1 = Process(path="path_to_executable1.exe", name="MockProcess1")

# Initialize the manager with the process
manager = ExeProcessManager()

# Add the process to the manager
manager.add_process(process1)

# Start the process
manager.start_process("MockProcess1")

# Stop the process
manager.stop_process("MockProcess1")
```

## **2. Using the Scheduler**
You can use the Scheduler to schedule actions like starting and stopping processes.
```python
from ExeProcessManager import ExeProcessManager, Process

# Initialize the process manager
manager = ExeProcessManager()

# Add a process to the manager
process1 = Process(path="path_to_executable1.exe", name="MockProcess1")
manager.add_process(process1)

# Schedule the process to start at 12:00 PM
manager.schedule_process("MockProcess1", "start", "12:00")

# Schedule the process to stop at 12:10 PM
manager.schedule_process("MockProcess1", "stop", "12:10")

# Schedule the process to restart at 12:15 PM
manager.schedule_process("MockProcess1", "restart", "12:15")

# Keep the scheduler running
while True:
    schedule.run_pending()
    time.sleep(1)
```
What this example does:

1. Start MockProcess1 at 12:00 PM.


2. Stop MockProcess1 at 12:10 PM.


3. Restart MockProcess1 at 12:15 PM.


4. Keeps the scheduler running to execute these actions.

## **3. Monitor and Auto-Restart Processes**
```python
from ExeProcessManager import ExeProcessManager, Process
import time

# Initialize the process manager and add a process
process1 = Process(path="path_to_executable1.exe", name="MockProcess1")
manager = ExeProcessManager()
manager.add_process(process1)

# Start the process
manager.start_process("MockProcess1")

# Monitor the process
manager.monitor_processes(check_interval=5)  # Check every 5 seconds

# Simulate process failure
time.sleep(10)  # Let the process run for 10 seconds
manager.stop_process("MockProcess1")  # Simulate process termination

# Monitor should detect and restart the process
time.sleep(2)  # Wait for auto-restart
```

## **Contributing**
If you'd like to contribute to this project, please fork the repository and submit a pull request with your changes. Ensure that your code passes all tests before submitting.

## **License**
This project is licensed under the MIT License - see the LICENSE file for details.



