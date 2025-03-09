"""
Advanced Logging System

Provides enhanced logging capabilities including:
- Structured JSON logging for machine parsing
- Console output with color-coding by log level
- Log rotation and retention management
- Custom formatting
- Context-aware logging with correlation IDs
"""

import os
import sys
import json
import logging
import logging.handlers
from typing import Dict, Any, Optional, Union, List
from datetime import datetime
from pathlib import Path
import threading
import traceback

# Try to import colorama for cross-platform colored terminal output
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False

class ContextFilter(logging.Filter):
    """Filter that adds contextual information to log records"""
    
    # Thread-local storage for context
    _local = threading.local()
    
    @classmethod
    def get_context(cls) -> Dict[str, Any]:
        """Get the current thread's logging context"""
        if not hasattr(cls._local, 'context'):
            cls._local.context = {}
        return cls._local.context
    
    @classmethod
    def set_context_value(cls, key: str, value: Any) -> None:
        """Set a value in the current thread's logging context"""
        context = cls.get_context()
        context[key] = value
    
    @classmethod
    def remove_context_value(cls, key: str) -> None:
        """Remove a value from the current thread's logging context"""
        context = cls.get_context()
        if key in context:
            del context[key]
    
    @classmethod
    def clear_context(cls) -> None:
        """Clear the current thread's logging context"""
        cls._local.context = {}
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add context values to the log record"""
        # Add thread_id
        record.thread_id = threading.get_ident()
        
        # Add context values
        context = self.get_context()
        for key, value in context.items():
            setattr(record, key, value)
        
        # Always return True to include the record
        return True

class ColorFormatter(logging.Formatter):
    """Formatter that adds colors to console output based on log level"""
    
    def __init__(self, fmt: str, datefmt: Optional[str] = None):
        super().__init__(fmt, datefmt)
        self.level_colors = {
            logging.DEBUG: Fore.CYAN if COLORAMA_AVAILABLE else '',
            logging.INFO: Fore.GREEN if COLORAMA_AVAILABLE else '',
            logging.WARNING: Fore.YELLOW if COLORAMA_AVAILABLE else '',
            logging.ERROR: Fore.RED if COLORAMA_AVAILABLE else '',
            logging.CRITICAL: Fore.RED + Style.BRIGHT if COLORAMA_AVAILABLE else '',
        }
    
    def format(self, record: logging.LogRecord) -> str:
        """Format the log record with appropriate color"""
        color = self.level_colors.get(record.levelno, '')
        reset = Style.RESET_ALL if COLORAMA_AVAILABLE else ''
        
        # Store the original message
        orig_msg = record.msg
        
        # Add color to the message
        record.msg = f"{color}{record.msg}{reset}"
        
        # Format the record
        result = super().format(record)
        
        # Restore the original message
        record.msg = orig_msg
        
        return result

class JsonFormatter(logging.Formatter):
    """Formatter that outputs logs as JSON objects"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as a JSON string"""
        log_data = {
            'timestamp': self.formatTime(record, self.datefmt),
            'level': record.levelname,
            'name': record.name,
            'message': record.getMessage(),
            'thread_id': getattr(record, 'thread_id', None),
        }
        
        # Add exception info if available
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': ''.join(traceback.format_exception(*record.exc_info))
            }
        
        # Add additional fields from context
        for key, value in record.__dict__.items():
            if key not in ['args', 'asctime', 'created', 'exc_info', 'exc_text', 
                          'filename', 'funcName', 'id', 'levelname', 'levelno', 
                          'lineno', 'module', 'msecs', 'message', 'msg', 'name', 
                          'pathname', 'process', 'processName', 'relativeCreated', 
                          'stack_info', 'thread', 'threadName']:
                log_data[key] = value
        
        return json.dumps(log_data)

class LogManager:
    """
    Manages logging for the entire application.
    
    Features:
    - Console output with color formatting
    - File output with rotation and retention
    - JSON structured logging for machine parsing
    - Context-aware logging with thread-local storage
    - Log correlation across multiple modules
    """
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """Singleton pattern to ensure only one LogManager instance"""
        if cls._instance is None:
            cls._instance = super(LogManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, log_level: str = "INFO", log_dir: Optional[str] = None):
        """Initialize the log manager"""
        # Skip re-initialization if already initialized
        if getattr(self, "_initialized", False):
            return
        
        # Set log directory
        if log_dir is None:
            # Use default location relative to current file
            current_dir = Path(__file__).parent.parent
            self._log_dir = current_dir / "data" / "logs"
        else:
            self._log_dir = Path(log_dir)
        
        # Create log directory if it doesn't exist
        os.makedirs(self._log_dir, exist_ok=True)
        
        # Map string log level to int
        log_level_dict = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        self._log_level = log_level_dict.get(log_level.upper(), logging.INFO)
        
        # Configure root logger
        self.root_logger = logging.getLogger()
        self.root_logger.setLevel(self._log_level)
        
        # Remove existing handlers
        for handler in self.root_logger.handlers[:]:
            self.root_logger.removeHandler(handler)
        
        # Add context filter to root logger
        self.context_filter = ContextFilter()
        self.root_logger.addFilter(self.context_filter)
        
        # Add console handler with color formatter
        self._setup_console_handler()
        
        # Add file handlers
        self._setup_file_handlers()
        
        # Set initialized flag
        self._initialized = True
        
        # Create logger for this class
        self.logger = logging.getLogger("LogManager")
        self.logger.info("Logging system initialized")
    
    def _setup_console_handler(self) -> None:
        """Set up console handler with color formatting"""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self._log_level)
        
        # Format string for console output
        fmt = "%(asctime)s [%(name)s] [%(levelname)s] %(message)s"
        
        # Apply color formatter if colorama is available
        if COLORAMA_AVAILABLE:
            formatter = ColorFormatter(fmt, datefmt="%Y-%m-%d %H:%M:%S")
        else:
            formatter = logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S")
        
        console_handler.setFormatter(formatter)
        self.root_logger.addHandler(console_handler)
    
    def _setup_file_handlers(self) -> None:
        """Set up file handlers with rotation and JSON formatting"""
        # Regular log file with rotation
        log_file = self._log_dir / "robotmower.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=5
        )
        file_handler.setLevel(self._log_level)
        
        fmt = "%(asctime)s [%(name)s] [%(levelname)s] [%(thread_id)d] %(message)s"
        formatter = logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S")
        file_handler.setFormatter(formatter)
        self.root_logger.addHandler(file_handler)
        
        # JSON log file with rotation
        json_log_file = self._log_dir / "robotmower.json.log"
        json_handler = logging.handlers.RotatingFileHandler(
            json_log_file, maxBytes=10*1024*1024, backupCount=5
        )
        json_handler.setLevel(self._log_level)
        
        json_formatter = JsonFormatter()
        json_handler.setFormatter(json_formatter)
        self.root_logger.addHandler(json_handler)
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger with the specified name"""
        return logging.getLogger(name)
    
    def set_context_value(self, key: str, value: Any) -> None:
        """Set a value in the current thread's logging context"""
        ContextFilter.set_context_value(key, value)
    
    def remove_context_value(self, key: str) -> None:
        """Remove a value from the current thread's logging context"""
        ContextFilter.remove_context_value(key)
    
    def clear_context(self) -> None:
        """Clear the current thread's logging context"""
        ContextFilter.clear_context()
    
    def set_correlation_id(self, correlation_id: Optional[str] = None) -> str:
        """
        Set a correlation ID for the current request/operation
        If not provided, a new UUID will be generated
        """
        if correlation_id is None:
            import uuid
            correlation_id = str(uuid.uuid4())
        
        self.set_context_value('correlation_id', correlation_id)
        return correlation_id
