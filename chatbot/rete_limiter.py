# rate_limiter: robust rate limiting system for both authenticated and anonymous users

import time
import hashlib
import re  # <-- Missing import!
from django.core.cache import cache
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta


class RateLimiter:
    def __init__(self, max_requests=20, window_seconds=86400):
        """
        Initialize rate limiter.
        :param max_requests: Maximum number of requests allowed per window.
        :param window_seconds: Time window in seconds (default: 24 hours = 86400).
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    def _get_cache_key(self, request):
        """Generate cache key based on user identity."""
        # For authenticated users
        if request.user.is_authenticated:
            return f"rl:user:{request.user.id}"

        # For anonymous users: use hashed session ID or IP address
        session_id = request.COOKIES.get('sessionid')
        if session_id:
            return f"rl:session:{hashlib.sha256(session_id.encode()).hexdigest()}"

        # Fallback to client IP
        ip = self._get_client_ip(request)
        return f"rl:ip:{hashlib.sha256(ip.encode()).hexdigest()}"

    def _get_client_ip(self, request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
        return ip

    def check_rate_limit(self, request):
        """Check if the request exceeds the rate limit."""
        cache_key = self._get_cache_key(request)

        # Get current request data from cache
        request_data = cache.get(cache_key)

        if not request_data:
            # Initialize new counter
            request_data = {
                'count': 1,
                'window_start': time.time()
            }
            cache.set(cache_key, request_data, self.window_seconds)
            return True

        current_time = time.time()

        # Check if the window has expired
        if current_time - request_data['window_start'] > self.window_seconds:
            # Reset counter for new window
            request_data = {
                'count': 1,
                'window_start': current_time
            }
            cache.set(cache_key, request_data, self.window_seconds)
            return True

        # Check if limit exceeded
        if request_data['count'] >= self.max_requests:
            return False

        # Increment counter and update cache with remaining TTL
        request_data['count'] += 1
        time_remaining = self.window_seconds - (current_time - request_data['window_start'])
        cache.set(cache_key, request_data, int(time_remaining))

        return True

    def get_remaining_requests(self, request):
        """Get the number of remaining requests in current window."""
        cache_key = self._get_cache_key(request)
        request_data = cache.get(cache_key)

        if not request_data:
            return self.max_requests

        current_time = time.time()

        # If window has expired, reset
        if current_time - request_data['window_start'] > self.window_seconds:
            return self.max_requests

        return max(0, self.max_requests - request_data['count'])