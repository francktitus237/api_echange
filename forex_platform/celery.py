import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'forex_platform.settings')

app = Celery('forex_platform')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
