"""
Initialize Celery application with beat schedule configuration.

This module configures the Celery application with periodic tasks.
When run as a script, it starts the Celery worker.
"""

from .celery import celery
from .beat_schedule import get_beat_schedule

celery.conf.beat_schedule = get_beat_schedule()

if __name__ == "__main__":
    celery.start()
