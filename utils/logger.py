#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Logger Utility Module

This module provides logging functionality for the WhatsApp Group Summary Bot.
It sets up a configured logger that writes to both console and file.
"""

import os
import logging
import logging.handlers
from typing import Optional
import colorlog


def setup_logger(log_level: str = 'INFO',
                 log_file: Optional[str] = None,
                 max_file_size: int = 10 * 1024 * 1024,  # 10 MB
                 backup_count: int = 5) -> logging.Logger:
    """
    Set up and configure logger
    
    Args:
        log_level (str, optional): Logging level. Defaults to 'INFO'.
        log_file (str, optional): Path to log file. Defaults to None.
        max_file_size (int, optional): Maximum log file size in bytes. Defaults to 10MB.
        backup_count (int, optional): Number of backup log files. Defaults to 5.
        
    Returns:
        logging.Logger: Configured logger
    """
    # Convert string log level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create logger
    logger = logging.getLogger('whatsapp_bot')
    logger.setLevel(numeric_level)
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create formatter for console with colors
    console_formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # If no log file specified, use default in debug_logs directory
    if not log_file:
        # Ensure debug_logs directory exists
        os.makedirs('debug_logs', exist_ok=True)
        log_file = os.path.join('debug_logs', 'whatsapp_bot.log')
    
    # Create log directory if it doesn't exist
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    # Create formatter for file (without colors)
    file_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Create file handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_file_size,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Log initial message
    logger.debug(f"Logger initialized with level {log_level}")
    
    return logger 