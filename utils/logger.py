"""
Logger Module

This module provides logging utilities for the fuzzing framework, including
command output logging and general application logging.
"""

import subprocess
import threading
import time
import os
import sys
import logging
from typing import Optional, List


class CommandLogger:
    """
    Logger for capturing and recording output from subprocess commands.
    
    This class runs a command in a subprocess and logs its output to a file
    in real-time. It's particularly useful for logging SmartThings CLI commands.
    """
    
    def __init__(self, command: List[str], log_file_name: str):
        """
        Initialize the CommandLogger.
        
        Args:
            command: The command to run as a list of strings
            log_file_name: Name of the file to log output
        """
        self.command = command
        self.log_file_name = log_file_name
        self.process: Optional[subprocess.Popen] = None
        self.log_file = None
        self.stop_logging = False

    def start(self) -> None:
        """Start the subprocess and begin logging its output."""
        os.makedirs(os.path.dirname(self.log_file_name), exist_ok=True)
        self.log_file = open(self.log_file_name, 'w')

        self.process = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        # Start a separate thread for logging
        self.logging_thread = threading.Thread(target=self._log_output)
        self.logging_thread.start()

        print(f'Logging to {self.log_file_name}... Press "Enter" to stop.')

    def send_input(self, user_input: str) -> None:
        """
        Send input to the subprocess.
        
        Args:
            user_input: Input string to send to the process
        """
        if self.process and self.process.stdin:
            self.process.stdin.write(f'{user_input}\n')
            self.process.stdin.flush()

    def _log_output(self) -> None:
        """Log the output of the subprocess in real-time."""
        for line in iter(self.process.stdout.readline, ''):
            if self.stop_logging:
                break
            print(line, end='')
            self.log_file.write(line)
            self.log_file.flush()

    def stop(self) -> None:
        """Stop logging and terminate the subprocess."""
        self.stop_logging = True
        if self.process:
            self.process.terminate()
        if hasattr(self, 'logging_thread'):
            self.logging_thread.join()
        if self.log_file:
            self.log_file.close()
        print("\nLogging stopped.")


class Logger:
    """
    General-purpose logger for application output.
    
    This class redirects stdout to both console and log file.
    """
    
    def __init__(self, log_file_name: str):
        """
        Initialize the Logger.
        
        Args:
            log_file_name: Name of the file to log output
        """
        self.log_file_name = log_file_name
        self.log_file = None
        self.stop_logging = False

        os.makedirs(os.path.dirname(log_file_name), exist_ok=True)
        
        # Set up logging configuration
        logging.basicConfig(
            filename=log_file_name,
            level=logging.DEBUG,
            encoding='utf-8',
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger()

        # Redirect stdout to the logger
        sys.stdout = self._LogWriter(self.logger.info)

    def start(self) -> None:
        """Start logging."""
        os.makedirs(os.path.dirname(self.log_file_name), exist_ok=True)
        self.log_file = open(self.log_file_name, 'w')
        print(f"Started logging to {self.log_file_name}...")

    def stop(self) -> None:
        """Stop logging."""
        self.stop_logging = True
        if self.log_file:
            self.log_file.close()

    class _LogWriter:
        """Internal class to write to both log file and console."""
        
        def __init__(self, log_function):
            self.log_function = log_function
        
        def write(self, message: str) -> None:
            """
            Write log message to file and console.
            
            Args:
                message: Message to write
            """
            if message != '\n':  # Avoid empty lines
                self.log_function(message.strip())  # Write to log file
                sys.__stdout__.write(message)  # Write to terminal

        def flush(self) -> None:
            """Flush the buffer."""
            pass


class FileLogger:
    """
    Simple file-based logger using Python's logging module.
    
    This is a lightweight logger for basic file logging needs.
    """
    
    level_relations = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'crit': logging.CRITICAL
    }

    def __init__(self, filename: str, level: str = 'info', fmt: str = '%(message)s'):
        """
        Initialize the FileLogger.
        
        Args:
            filename: Log file path
            level: Logging level (debug, info, warning, error, crit)
            fmt: Log message format
        """
        self.logger = logging.getLogger(filename)
        self.logger.setLevel(self.level_relations.get(level, logging.INFO))

        formatter = logging.Formatter(fmt)
        file_handler = logging.FileHandler(filename=filename, encoding='utf-8')
        file_handler.setFormatter(formatter)

        if not self.logger.handlers:
            self.logger.addHandler(file_handler)


def start_logging_st(
    cmd: List[str] = ['smartthings', 'edge:drivers:logcat'],
    log_file_name: str = 'output_st.log'
) -> CommandLogger:
    """
    Start logging SmartThings Edge Driver output.
    
    This is a convenience function that sets up logging for SmartThings CLI
    commands with appropriate input handling.
    
    Args:
        cmd: Command to run
        log_file_name: Log file path
        
    Returns:
        CommandLogger instance
    """
    logger = CommandLogger(cmd, log_file_name)
    logger.start()

    if 'edge:drivers:logcat' in cmd:
        time.sleep(1)
        logger.send_input('1')  # Select driver
        time.sleep(3)
        logger.send_input('10')  # Select log level

    return logger

