import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'simpextrac.settings')

# Create the Celery app
app = Celery('simpextrac')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps
app.autodiscover_tasks()

# Celery Beat schedule configuration
app.conf.beat_schedule = {
    # Example: Run every 30 minutes
    'scheduled-scraping': {
        'task': 'jobs.tasks.run_scheduled_scraping',
        'schedule': 30.0 * 60,  # 30 minutes
    },
    # Clean up old task results every day
    'cleanup-old-results': {
        'task': 'jobs.tasks.cleanup_old_results',
        'schedule': 24.0 * 60 * 60,  # 24 hours
    },
}

app.conf.timezone = 'UTC'

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')