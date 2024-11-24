import subprocess
import time
import os
import logging
import signal
import psutil
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from threading import Thread


class ExeProcessManager:
    def __init__(self, exe_path, log_file="process_manager.log", email_config=None):
        self.exe_path = exe_path
        self.process = None
        self.is_running = False
        
        # Email notification settings
        self.email_config = email_config or {}
        
        # Set up logging
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        logging.info("Process Manager initialized.")
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
            self.send_email("Process Start Error", str(e))
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
            self.send_email("Process Stop Error", str(e))
            return False

    def restart_process(self):
        """Restart the .exe process."""
        if self.stop_process():
            time.sleep(1)  # Wait a moment before restarting
            return self.start_process()
        else:
            logging.error("Failed to restart process.")
            self.send_email("Process Restart Failed", "The process could not be restarted.")
            return False

    def auto_restart(self, check_interval=5):
        """Automatically restart the process if it stops unexpectedly."""
        def auto_restart_thread():
            try:
                while True:
                    if not self.is_running:
                        logging.info("Process stopped unexpectedly. Restarting...")
                        self.start_process()
                    
                    time.sleep(check_interval)  # Check every interval seconds
            except KeyboardInterrupt:
                logging.info("Auto-restart stopped manually.")
                self.stop_process()
        
        Thread(target=auto_restart_thread, daemon=True).start()

    def monitor_process(self):
        """Monitor the process health."""
        try:
            if self.process and self.is_running:
                self.process.poll()  # Check if the process is still running
                if self.process.returncode is not None:
                    logging.warning("Process has terminated unexpectedly.")
                    self.is_running = False
                    self.send_email("Process Terminated", "The process stopped unexpectedly.")
                    return False
                return True
            else:
                logging.warning("Process is not running.")
                return False
        except Exception as e:
            logging.error(f"Error monitoring process: {e}")
            self.send_email("Monitoring Error", str(e))
            return False

    def monitor_resource_usage(self, check_interval=5):
        """Monitor the process resource usage (CPU, memory)."""
        def resource_monitor_thread():
            try:
                while self.is_running:
                    if self.process and psutil.pid_exists(self.process.pid):
                        proc = psutil.Process(self.process.pid)
                        cpu = proc.cpu_percent(interval=1)
                        memory = proc.memory_info().rss / (1024 * 1024)  # Convert to MB
                        logging.info(f"Process Resource Usage - CPU: {cpu:.2f}% Memory: {memory:.2f} MB")
                    else:
                        logging.warning("Process not found during resource monitoring.")
                        self.is_running = False
                    time.sleep(check_interval)
            except Exception as e:
                logging.error(f"Resource monitoring error: {e}")
        
        Thread(target=resource_monitor_thread, daemon=True).start()

    def send_email(self, subject, body):
        """Send an email notification."""
        if not self.email_config.get("enabled"):
            return
        
        try:
            sender_email = self.email_config["sender_email"]
            receiver_email = self.email_config["receiver_email"]
            smtp_server = self.email_config["smtp_server"]
            smtp_port = self.email_config["smtp_port"]
            smtp_password = self.email_config["smtp_password"]

            # Create email message
            msg = MIMEMultipart()
            msg["From"] = sender_email
            msg["To"] = receiver_email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            # Send email
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(sender_email, smtp_password)
                server.send_message(msg)
                logging.info(f"Email sent: {subject}")
        except Exception as e:
            logging.error(f"Error sending email: {e}")

    def graceful_shutdown(self):
        """Gracefully shut down the process manager."""
        try:
            logging.info("Shutting down the process manager...")
            if self.is_running:
                self.stop_process()
            logging.info("Shutdown complete.")
        except Exception as e:
            logging.error(f"Error during shutdown: {e}")

