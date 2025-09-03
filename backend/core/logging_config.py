"""
Logging configuration for both local and GCP deployment
"""

import os
import logging
import sys
from typing import Dict, Any
import json
from datetime import datetime

def setup_logging(app_name: str = "rag-backend", env: str = None) -> None:
    """
    Configure logging for the application
    
    - In development: Uses console output with detailed formatting
    - In production/GCP: Uses structured JSON logging for Cloud Logging
    """
    
    env = env or os.getenv("APP_ENV", "development")
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # Clear existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers = []
    
    if env == "production":
        # Production/GCP: Use structured JSON logging
        setup_gcp_logging(app_name, log_level)
    else:
        # Development: Use console logging with colors
        setup_console_logging(log_level)
    
    # Set logging level for third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.INFO)
    logging.getLogger("supabase").setLevel(logging.INFO)
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured for {env} environment at {log_level} level")


class GCPFormatter(logging.Formatter):
    """JSON formatter for Google Cloud Logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON for GCP"""
        log_obj = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "severity": record.levelname,
            "message": record.getMessage(),
            "logging.googleapis.com/sourceLocation": {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName
            },
            "python": {
                "module": record.module,
                "logger": record.name
            }
        }
        
        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, "extra_fields"):
            log_obj.update(record.extra_fields)
        
        return json.dumps(log_obj)


class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record: logging.LogRecord) -> str:
        """Add colors to log output"""
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_gcp_logging(app_name: str, log_level: str) -> None:
    """Configure structured logging for GCP"""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(GCPFormatter())
    
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level))
    root_logger.addHandler(handler)
    
    # Add app name to all logs
    old_factory = logging.getLogRecordFactory()
    
    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        record.extra_fields = {"app": app_name}
        return record
    
    logging.setLogRecordFactory(record_factory)


def setup_console_logging(log_level: str) -> None:
    """Configure console logging for development"""
    handler = logging.StreamHandler(sys.stdout)
    
    # Detailed format for development
    format_str = (
        "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
    )
    
    formatter = ColoredFormatter(format_str, datefmt="%H:%M:%S")
    handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level))
    root_logger.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name"""
    return logging.getLogger(name)


# Utility function for structured logging
def log_with_context(logger: logging.Logger, level: str, message: str, **context):
    """
    Log a message with additional context
    
    Example:
        log_with_context(logger, "INFO", "File uploaded", 
                        file_id="123", size=1024, user="test@example.com")
    """
    extra = {"extra_fields": context} if context else {}
    getattr(logger, level.lower())(message, extra=extra)