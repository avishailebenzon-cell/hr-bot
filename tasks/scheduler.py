import logging
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class TaskScheduler:
    """Manages scheduled tasks using APScheduler"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler(
            jobstores={"default": MemoryJobStore()},
            timezone=settings.timezone,
        )
        self._registered_jobs = []

    def add_job(self, func, trigger, job_id: str = None, **kwargs):
        """Add a scheduled job"""
        job = self.scheduler.add_job(
            func,
            trigger,
            id=job_id or func.__name__,
            replace_existing=True,
            **kwargs
        )
        self._registered_jobs.append(job)
        logger.info(f"Added job: {job.id} (next run: {job.next_run_time})")
        return job

    async def start(self):
        """Start the scheduler"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Task scheduler started")

    async def stop(self):
        """Stop the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Task scheduler stopped")

    def get_jobs(self):
        """Get all registered jobs"""
        return self.scheduler.get_jobs()

# Singleton instance
task_scheduler = TaskScheduler()
