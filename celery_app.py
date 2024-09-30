from celery import Celery
from celery.schedules import crontab

celery_app = Celery('tasks')
celery_app.conf.broker_url = 'redis://redis:6379/0'
celery_app.conf.result_backend = 'redis://redis:6379/0'

celery_app.conf.beat_schedule = {
    'check-notifications-every-minute': {
        'task': 'tasks.check_and_send_notifications',
        'schedule': crontab(minute='*'),
    },
}

celery_app.conf.timezone = 'UTC'

celery_app.autodiscover_tasks(['tasks'])

if __name__ == '__main__':
    celery_app.start()