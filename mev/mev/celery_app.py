import os
from celery import Celery
from django.apps import apps

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mev.settings')

app = Celery('mev')
app.conf.update(
    broker_url='amqp://localhost',
    result_backend='rpc://localhost',
    accept_content=['json'],
    task_serializer='json',
    result_serializer='json',
    worker_hijack_root_logger = False,
    enable_utc=True
)
app.autodiscover_tasks(
    lambda: [n.name for n in apps.get_app_configs()],
    related_name = 'async_tasks'
)

# For cron jobs like cleanup, polling for jobs
app.conf.beat_schedule = {}


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
