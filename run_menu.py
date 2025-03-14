#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Menu Launcher for WhatsApp Group Summary Bot

This script launches the interactive menu interface for the WhatsApp Group Summary Bot.
It provides access to generate summaries, change settings, debug, and more.
"""

import os
import sys
import logging
from dotenv import load_dotenv
from utils.logger import setup_logger
from menu.core import run_main_menu

if __name__ == "__main__":
    try:
        # Setup logging
        logger = setup_logger("INFO")
        logger.info("Starting WhatsApp Group Summary Bot Menu...")
        
        # Load environment variables
        load_dotenv(override=True)
        
        # Run the main menu
        run_main_menu()
        
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        print(f"\n❌ Error: {str(e)}")
        print("\nThe application encountered a fatal error. Check the logs for details.")
        input("\nPress Enter to exit...")
        sys.exit(1) 