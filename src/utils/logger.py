"""
Logging configuration for Claude conversation importer
"""
import sys
from pathlib import Path
from loguru import logger
from config.settings import get_settings, ensure_log_directory


def setup_logger():
    """Setup application logger with file and console output"""
    settings = get_settings()
    
    # Ensure log directory exists
    ensure_log_directory()
    
    # Remove default handler
    logger.remove()
    
    # Console handler with colors
    logger.add(
        sys.stdout,
        level=settings.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True
    )
    
    # File handler
    logger.add(
        settings.log_file,
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="10 MB",
        retention="30 days",
        compression="zip"
    )
    
    return logger


def get_logger(name: str):
    """Get a logger for a specific module"""
    return logger.bind(name=name)