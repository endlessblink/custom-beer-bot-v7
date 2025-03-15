#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
WhatsApp Summary Bot Activator

This is a simple script to start the WhatsApp Summary Bot.
It's designed to be easy to remember and use.

Usage:
    python activate.py        # Run the bot in normal mode
    python activate.py --background  # Run the bot in background mode
"""

import sys
import os

if __name__ == "__main__":
    # Just run the original script directly instead of using exec
    # This avoids encoding issues
    args = ' '.join(sys.argv[1:])
    os.system(f"python summary_menu_new.py {args}") 