# production_settings.py
import os
from .settings import *

# Security settings
DEBUG = False
ALLOWED_HOSTS = [
    'your-production-domain.com',
    'localhost',
    '127.0.0.1'
]

# Database configuration with connection pooling
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'rag_chatbot'),
        'USER': os.getenv('DB_USER', 'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
        'OPTIONS': {
            'sslmode': 'require',
            # ✅ "pool" is not a valid key in PostgreSQL OPTIONS
            # Instead, use connection pooling via psycopg2 pool or external tools (e.g., PgBouncer)
            # Django doesn't natively support `pool` config like this.
            # Remove the 'pool' section unless you're using a custom adapter.
        }
    }
}

# Redis configuration with clustering support
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.ShardClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 150,
                'timeout': 30,
                'retry_on_timeout': True,
            },
            'SERIALIZER': 'django_redis.serializers.MsgPackSerializer'
        }
    }
}

# Celery configuration
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ['msgpack']
CELERY_TASK_SERIALIZER = 'msgpack'
CELERY_RESULT_SERIALIZER = 'msgpack'
CELERY_TASK_COMPRESSION = 'zlib'
CELERY_WORKER_CONCURRENCY = 16  # Match your CPU core count
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000
CELERY_BROKER_TRANSPORT_OPTIONS = {
    'visibility_timeout': 3600,
    'max_retries': 3
}

# RAG System Settings
RAG_SETTINGS = {
    'EMBEDDING_MODEL': 'sentence-transformers/all-MiniLM-L6-v2',
    'VECTOR_STORE_PATH': os.path.join(BASE_DIR, 'data', 'vector_store'),
    'DOCUMENTS_PATH': os.path.join(BASE_DIR, 'data', 'documents'),
    'MAX_DOCUMENT_SIZE': 40 * 1024 * 1024,  # 40MB
    'MAX_DOCUMENTS': 500,
    'CHUNK_SIZE': 512,
    'CHUNK_OVERLAP': 64,
    'TOP_K_RESULTS': 5,
    'SIMILARITY_THRESHOLD': 0.65,
    'ENTITY_EXTRACTION': True,
    'CROSS_DOCUMENT_REASONING': True
}

# Rate limiting configuration
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = 'default'
RATELIMIT_DEFAULT = '20/d'  # 20 requests per day

# Monitoring settings
SENTRY_DSN = os.getenv('SENTRY_DSN', '')
METRICS_ENABLED = True
METRICS_INTERVAL = 60  # seconds