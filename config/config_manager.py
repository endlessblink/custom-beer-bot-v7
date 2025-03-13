#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Configuration Manager Module

This module handles the loading, validation, and access to configuration settings
for the WhatsApp Group Summary Bot. It provides a uniform interface for accessing
configuration values from environment variables and runtime settings.
"""

import os
import json
import logging
from typing import Any, Dict, Optional, Union


class ConfigManager:
    """
    Configuration Manager for WhatsApp Bot
    
    Handles loading and accessing configuration from environment variables 
    and runtime settings.
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize the configuration manager
        
        Args:
            config_file (str, optional): Path to config file. Defaults to None.
        """
        self.logger = logging.getLogger(__name__)
        
        # Runtime configuration (can be changed during execution)
        self.runtime_config: Dict[str, Any] = {}
        
        # Load config file if provided
        if config_file and os.path.exists(config_file):
            self._load_config_file(config_file)
    
    def _load_config_file(self, config_file: str) -> None:
        """
        Load configuration from file
        
        Args:
            config_file (str): Path to config file
        """
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
                
            # Merge with runtime config
            self.runtime_config.update(file_config)
            self.logger.info(f"Loaded configuration from {config_file}")
            
        except Exception as e:
            self.logger.error(f"Error loading config file {config_file}: {str(e)}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value
        
        Checks runtime config first, then environment variables.
        
        Args:
            key (str): Configuration key
            default (Any, optional): Default value if key not found. Defaults to None.
            
        Returns:
            Any: Configuration value
        """
        # Check runtime config first
        if key in self.runtime_config:
            return self.runtime_config[key]
        
        # Then check environment variables
        env_value = os.environ.get(key)
        if env_value is not None:
            return env_value
        
        # Return default if key not found
        return default
    
    def set(self, key: str, value: Any) -> None:
        """
        Set runtime configuration value
        
        Args:
            key (str): Configuration key
            value (Any): Configuration value
        """
        self.runtime_config[key] = value
        self.logger.debug(f"Set config {key}={value}")
    
    def save(self, config_file: str) -> bool:
        """
        Save runtime configuration to file
        
        Args:
            config_file (str): Path to config file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self.runtime_config, f, indent=2)
            
            self.logger.info(f"Saved configuration to {config_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving config to {config_file}: {str(e)}")
            return False
    
    def get_all(self) -> Dict[str, Any]:
        """
        Get all configuration values (environment and runtime)
        
        Returns:
            Dict[str, Any]: All configuration values
        """
        # Start with environment variables
        all_config = {
            key: value 
            for key, value in os.environ.items() 
            if not key.startswith('_')  # Skip internal variables
        }
        
        # Override with runtime config
        all_config.update(self.runtime_config)
        
        return all_config
    
    def validate_required(self, required_keys: list) -> bool:
        """
        Validate that all required keys are present
        
        Args:
            required_keys (list): List of required keys
            
        Returns:
            bool: True if all required keys are present, False otherwise
        """
        missing = []
        
        for key in required_keys:
            if self.get(key) is None:
                missing.append(key)
        
        if missing:
            self.logger.error(f"Missing required configuration: {', '.join(missing)}")
            return False
        
        return True 