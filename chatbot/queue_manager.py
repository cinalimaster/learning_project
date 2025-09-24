import time
import uuid
import threading
import queue
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class QueryQueue:
    """Redis-backed priority queue for managing user requests"""

    def __init__(self, max_size=1000, priority_weights=None):
        """
        Initialize the query queue.
        :param max_size: Maximum number of pending requests.
        :param priority_weights: Dictionary of priority weights (higher = higher priority).
        """
        self.max_size = max_size
        self.priority_weights = priority_weights or {
            'high': 3.0,    # Urgent queries (short, simple)
            'medium': 2.0,  # Standard queries
            'low': 1.0      # Complex queries requiring more processing
        }
        self.redis = cache.client.get_client()
        self.queue_key = "rag:query_queue"
        self.status_key_prefix = "rag:query_status:"
        self.lock = threading.Lock()

    def estimate_complexity(self, query):
        """Estimate query complexity to determine priority."""
        # Simple heuristics for complexity estimation
        length_score = min(1.0, len(query) / 200)  # Longer queries might be more complex

        # Check for entity extraction keywords
        entity_keywords = ['kim', 'nerede', 'adres', 'telefon', 'email', 'url', 'link']
        entity_score = 1.5 if any(kw in query.lower() for kw in entity_keywords) else 1.0

        # Check for simple vs complex question types
        simple_questions = ['nasıl', 'ne zaman', 'nerede']
        complexity_score = 0.8 if any(q in query.lower() for q in simple_questions) else 1.2

        # Overall complexity score (higher = more complex)
        complexity = length_score * entity_score * complexity_score

        # Determine priority based on complexity
        if complexity < 1.0:
            return 'high', complexity
        elif complexity < 1.5:
            return 'medium', complexity
        else:
            return 'low', complexity

    def enqueue(self, query, user_id=None):
        """
        Add a query to the queue with appropriate priority.
        :param query: The user's input query string.
        :param user_id: Optional user identifier.
        :return: request_id if successful, None if queue is full.
        """
        with self.lock:
            # Check queue size
            current_size = self.redis.zcard(self.queue_key)
            if current_size >= self.max_size:
                logger.warning("Query queue is full. Rejecting new request.")
                return None

            # Generate unique request ID
            request_id = str(uuid.uuid4())
            timestamp = time.time()

            # Determine priority and calculate score
            priority, complexity = self.estimate_complexity(query)
            priority_score = timestamp + (1.0 / self.priority_weights[priority])

            # Store request details
            request_data = {
                'query': query,
                'user_id': user_id,
                'timestamp': str(timestamp),
                'complexity': str(complexity),
                'status': 'queued'
            }

            # Save to Redis
            self.redis.hset(f"{self.status_key_prefix}{request_id}", mapping=request_data)
            self.redis.zadd(self.queue_key, {request_id: priority_score})

            logger.info(
                f"Enqueued query {request_id} with priority {priority} "
                f"(score: {priority_score:.4f})"
            )
            return request_id

    def dequeue(self):
        """
        Get the next query from the queue based on priority.
        :return: (request_id, request_data) if available, None otherwise.
        """
        with self.lock:
            # Get highest priority request (lowest score)
            request_ids = self.redis.zrange(self.queue_key, 0, 0, withscores=False)
            if not request_ids:
                return None

            request_id = request_ids[0].decode('utf-8')

            # Remove from queue
            self.redis.zrem(self.queue_key, request_id)

            # Update status to "processing"
            self.redis.hset(f"{self.status_key_prefix}{request_id}", "status", "processing")
            self.redis.expire(f"{self.status_key_prefix}{request_id}", 3600)  # Expire after 1 hour

            # Retrieve request data
            data = self.redis.hgetall(f"{self.status_key_prefix}{request_id}")
            if not data:
                return None

            # Decode keys and values from bytes
            decoded_data = {k.decode('utf-8'): v.decode('utf-8') for k, v in data.items()}

            logger.info(f"Dequeued request {request_id} for processing.")
            return request_id, decoded_data

    def update_status(self, request_id, status, result=None):
        """
        Update the status of a request.
        :param request_id: The unique ID of the request.
        :param status: Current status ('completed', 'failed', etc.).
        :param result: Optional result to store.
        """
        data = {'status': status}
        if result:
            data['result'] = result
            data['completed_at'] = str(timezone.now())

        self.redis.hset(f"{self.status_key_prefix}{request_id}", mapping=data)

        # Keep the record for 24 hours if completed or failed
        if status in ['completed', 'failed']:
            self.redis.expire(f"{self.status_key_prefix}{request_id}", 86400)  # 24 hours

    def get_status(self, request_id):
        """
        Get the current status of a request.
        :param request_id: The unique ID of the request.
        :return: Dictionary of status data, or None if not found.
        """
        data = self.redis.hgetall(f"{self.status_key_prefix}{request_id}")
        if not data:
            return None

        # Decode all keys and values
        return {k.decode('utf-8'): v.decode('utf-8') for k, v in data.items()}