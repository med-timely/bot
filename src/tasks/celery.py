from celery import Celery
from src.config import settings

celery = Celery(
    "medtimely",
    broker=settings.redis.url.encoded_string(),  # pylint: disable=no-member
    backend=settings.redis.url.encoded_string(),  # pylint: disable=no-member
    include=["src.tasks.notifications"],
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
