import os
from celery import Celery
from celery.signal import setup_logging

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project.settings')

app = Celery('rag_chatbot')
app.config_from_object('django.conf:settings', namespace='CELERY')

# Configure queue routing for different task types
app.conf.task_routes = {
    'chatbot.task.process_query': {'queue': 'query_queue'},
    'chatbot.task.process_document': {'queue': 'document_queue'},
    'chatbot.task.update_embeddings': {'queue': 'embedding_queue'},
}

# Optimize worker configration for 16 core CPU
app.conf.worker_prefetch_multiplier = 1 # Better for CPU bound tasks
app.conf.task_ack_late = True # Acknowled after task completion
app.conf.worker_mask_tasks_per_child = 1000 # Prevent memory leaks
app.conf.worker_concurrency = 16 # This should be equal to your CPU cores
app.conf.broker_pool_limit = 100 # Higher for Redis


# Configure task time limits based on the task type
app.conf.task_time_limit = 300 # 5 minutes for most tasks
app.conf.task_soft_time_limit = 240 # 4 minutes for soft limit


# Enable compression for large task payloads
app.conf.accept_content = ['json', 'msgpack']
app.conf.task_serializer = 'msgpack'
app.conf.result_serializer = 'msgpack'


# Setup Logging
@setup_logging.connect
def setup_loggers(*args, **kwargs):
    from logging.config import dictConfig
    dictConfig({
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s [%(levelname)s %(name)s: %(message)s'
            },
        },
        'handlers': {
            'default': {
                'level': 'INFO',
                'class': 'logging.StreamHandler',
                'formatter': 'standard'
            },
        },
        'loggers': {
            '': {
                'handlers': ['default'],
                'level': 'INFO',
                'propagate': True
            }
        }
    })
