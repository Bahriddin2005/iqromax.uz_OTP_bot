"""
iqromax.uz OTP Bot - Logging Configuration
Structured logging setup for production
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path

from src.config import settings, BASE_DIR


def setup_logging():
    """
    Configure application logging
    
    Sets up:
    - Console handler with colored output
    - File handler with rotation
    - Different log levels for different components
    """
    
    # Create logs directory
    log_dir = BASE_DIR / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Log format
    detailed_format = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    simple_format = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S"
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
    console_handler.setFormatter(simple_format)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation
    if settings.LOG_FILE:
        log_file = BASE_DIR / settings.LOG_FILE
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            filename=str(log_file),
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_format)
        root_logger.addHandler(file_handler)
    
    # Error log file (separate file for errors only)
    error_log_file = log_dir / "error.log"
    error_handler = RotatingFileHandler(
        filename=str(error_log_file),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_format)
    root_logger.addHandler(error_handler)
    
    # Suppress noisy loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.DEBUG if settings.DEBUG else logging.WARNING
    )
    
    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured - Level: {settings.LOG_LEVEL}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    
    return root_logger


class RequestLogger:
    """
    Context manager for request logging
    """
    
    def __init__(self, request_id: str, endpoint: str):
        self.request_id = request_id
        self.endpoint = endpoint
        self.logger = logging.getLogger("request")
        self.start_time = None
    
    def __enter__(self):
        import time
        self.start_time = time.time()
        self.logger.info(f"[{self.request_id}] Started: {self.endpoint}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        import time
        duration = time.time() - self.start_time
        
        if exc_type:
            self.logger.error(
                f"[{self.request_id}] Failed: {self.endpoint} "
                f"({duration:.3f}s) - {exc_type.__name__}: {exc_val}"
            )
        else:
            self.logger.info(
                f"[{self.request_id}] Completed: {self.endpoint} ({duration:.3f}s)"
            )
        
        return False  # Don't suppress exceptions


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        logging.Logger: Configured logger
    """
    return logging.getLogger(name)
