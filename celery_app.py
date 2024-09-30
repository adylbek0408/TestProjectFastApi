from celery import Celery
import os
from celery.schedules import crontab

celery_app = Celery('my_project',
                    backend=os.getenv("REDIS_URL", 'redis://redis:6379/0'),
                    broker=os.getenv("REDIS_URL", 'redis://redis:6379/0'))

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_annotations={'*': {'rate_limit': '10/s'}},
    worker_concurrency=1,
    worker_prefetch_multiplier=1,
    task_default_queue='default',
    task_create_missing_queues=True,
    broker_pool_limit=None,
)

# Автоматически обнаруживаем задачи в модуле tasks
celery_app.autodiscover_tasks(['tasks'])

# Определяем расписание задач для Celery Beat
celery_app.conf.beat_schedule = {
    'check-notifications-every-minute': {
        'task': 'check_and_send_notifications',
        'schedule': crontab(minute='*'),
    },
}
