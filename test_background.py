#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test Background Mode

This script helps verify that the background mode of the bot is working properly.
It runs a simple test that logs activity every minute to verify the scheduler is working.
"""

import os
import time
import logging
import datetime
from summary_menu_new import BackgroundBot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug_logs/background_test.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('background_test')

def main():
    """Run a test of the background mode"""
    print("Starting background test...")
    logger.info("Background test started")
    
    # Create a BackgroundBot instance
    bot = BackgroundBot()
    bot.initialize()
    
    # Override the scheduled time to be 1 minute from now
    current_time = datetime.datetime.now()
    test_time = (current_time + datetime.timedelta(minutes=1)).strftime('%H:%M')
    
    # Save this as the scheduled time (temporary)
    original_time = os.environ.get('SCHEDULED_POST_TIME', '')
    os.environ['SCHEDULED_POST_TIME'] = test_time
    
    print(f"Setting test scheduled time to: {test_time} (1 minute from now)")
    logger.info(f"Test scheduled time set to: {test_time}")
    
    # Start a minute counter
    minute_counter = 0
    
    try:
        # Start the bot's scheduler
        bot.start()
        
        print("\nThe bot is now running in background test mode.")
        print("It will log activity every minute and should run the scheduled task soon.")
        print("Press Ctrl+C to stop the test.\n")
        
        # Keep the script running, log activity every minute
        while True:
            minute_counter += 1
            current_time_str = datetime.datetime.now().strftime('%H:%M:%S')
            
            print(f"[{current_time_str}] Bot active for {minute_counter} minute(s)...")
            logger.info(f"Bot active for {minute_counter} minute(s)")
            
            # Check next run time from scheduler
            if bot.scheduler and bot.scheduler.get_jobs():
                job = bot.scheduler.get_jobs()[0]
                next_run = job.next_run_time.strftime('%H:%M:%S')
                print(f"Next scheduled task will run at: {next_run}")
            
            # Sleep for 60 seconds
            time.sleep(60)
            
    except KeyboardInterrupt:
        print("\nTest stopped by user.")
        logger.info("Background test stopped by user")
    except Exception as e:
        print(f"\nError during test: {str(e)}")
        logger.error(f"Error during background test: {str(e)}")
    finally:
        # Restore original scheduled time
        if original_time:
            os.environ['SCHEDULED_POST_TIME'] = original_time
        else:
            os.environ.pop('SCHEDULED_POST_TIME', None)
            
        # Stop the bot if it's running
        if bot.running:
            bot.stop()
            
        print("\nTest completed. Check debug_logs/background_test.log for details.")

if __name__ == "__main__":
    main() 