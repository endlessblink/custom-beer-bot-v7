#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Scheduler Module

This module provides functionality for scheduling and managing summary tasks
for the WhatsApp Group Summary Bot.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional
import schedule


class SummaryScheduler:
    """
    Summary Scheduler for WhatsApp Bot
    
    This class provides methods for scheduling and managing summary tasks.
    """
    
    def __init__(self, 
                 summary_interval: int = 24, 
                 retry_delay: int = 60,
                 max_retries: int = 3):
        """
        Initialize the summary scheduler
        
        Args:
            summary_interval (int, optional): Hours between summaries. Defaults to 24.
            retry_delay (int, optional): Seconds between retries. Defaults to 60.
            max_retries (int, optional): Maximum number of retries. Defaults to 3.
        """
        self.summary_interval = summary_interval
        self.retry_delay = retry_delay
        self.max_retries = max_retries
        self.logger = logging.getLogger(__name__)
        
        # Clear any existing schedules
        schedule.clear()
        
        self.logger.info(f"Summary scheduler initialized with interval {summary_interval} hours")
    
    def schedule_summary(self, task: Callable, interval_hours: int) -> None:
        """
        Schedule a summary task
        
        Args:
            task (Callable): Task to schedule
            interval_hours (int): Hours between task executions
        """
        self.logger.info(f"Scheduling summary task every {interval_hours} hours")
        
        # Create a wrapper function that handles retries
        def task_with_retry():
            retries = 0
            while retries <= self.max_retries:
                try:
                    self.logger.info(f"Executing scheduled task (attempt {retries + 1})")
                    task()
                    return  # Success, exit retry loop
                except Exception as e:
                    retries += 1
                    self.logger.error(f"Task failed: {str(e)}")
                    
                    if retries <= self.max_retries:
                        self.logger.info(f"Retrying in {self.retry_delay} seconds...")
                        time.sleep(self.retry_delay)
                    else:
                        self.logger.error(f"Task failed after {retries} attempts")
        
        # Schedule the task
        schedule.every(interval_hours).hours.do(task_with_retry)
        
        # Also run immediately
        self.logger.info("Running initial task immediately")
        task_with_retry()
    
    def run_pending(self) -> None:
        """
        Run pending scheduled tasks
        """
        schedule.run_pending()
    
    def clear_schedule(self) -> None:
        """
        Clear all scheduled tasks
        """
        self.logger.info("Clearing all scheduled tasks")
        schedule.clear()
    
    def get_next_run(self) -> Optional[datetime]:
        """
        Get the next scheduled run time
        
        Returns:
            Optional[datetime]: Next run time or None if no tasks scheduled
        """
        jobs = schedule.get_jobs()
        if not jobs:
            return None
        
        # Find the job with the earliest next run time
        next_run = min(job.next_run for job in jobs)
        return next_run
    
    def time_until_next_run(self) -> Optional[timedelta]:
        """
        Get time until next scheduled run
        
        Returns:
            Optional[timedelta]: Time until next run or None if no tasks scheduled
        """
        next_run = self.get_next_run()
        if not next_run:
            return None
        
        now = datetime.now()
        return next_run - now 