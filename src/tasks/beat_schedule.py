from celery.schedules import crontab


def get_beat_schedule():
    """
    Returns the Celery beat schedule configuration.

    Defines a periodic task that sends medication reminders every 15 minutes
    with a 5-minute expiration time.

    Returns:
        dict: The beat schedule configuration dictionary
    """
    return {
        "send-medication-reminders": {
            "task": "src.tasks.notifications.send_medication_reminders",
            "schedule": crontab(minute="*/15"),  # Every 15 minutes
            "options": {"expires": 300},
        },
    }
