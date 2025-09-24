import logging
import time
import psutil
import GPUtil
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


class SystemMonitor:
    def __init__(self):
        self.metrics_key = 'system_metrics'
        self.alert_thresholds = {
            'cpu_usage': 90,              # Alert when > 90%
            'memory_usage': 90,           # Alert when > 90%
            'gpu_usage': 95,              # Alert when > 95%
            'gpu_memory': 95,             # Alert when > 95%
            'queue_size': 500,            # Alert when > 500
            'response_time': 8.0          # Alert when avg > 8 seconds
        }
        self.alert_cooldown = 300  # 5 minutes between alerts

    def collect_metrics(self):
        """Collect system metrics"""
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()

        # Memory metrics
        mem = psutil.virtual_memory()
        memory_usage = mem.percent

        # GPU metrics
        gpu_metrics = []
        try:
            gpus = GPUtil.getGPUs()
            for gpu in gpus:
                gpu_metrics.append({
                    'id': gpu.id,
                    'name': gpu.name,
                    'load': gpu.load * 100,
                    'memory_used': gpu.memoryUsed,
                    'memory_total': gpu.memoryTotal,
                    'memory_percent': (gpu.memoryUsed / gpu.memoryTotal) * 100,
                    'temperature': gpu.temperature
                })
        except Exception as e:
            logger.warning(f"Failed to get GPU metrics: {e}")
            gpu_metrics = None

        # Queue Metrics
        from chatbot.queue_manager import QueryQueue
        queue = QueryQueue()
        try:
            queue_size = queue.redis.zcard(queue.queue_key)
        except Exception as e:
            logger.warning(f"Failed to get queue size: {e}")
            queue_size = 0

        # Response time metrics
        response_times = cache.get('response_times', [])
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0.0

        # Build metrics dictionary
        metrics = {
            'timestamp': time.time(),
            'cpu': {
                'usage_percent': cpu_percent,
                'count': cpu_count
            },
            'memory': {
                'usage_percent': memory_usage,
                'total': mem.total,
                'available': mem.available
            },
            'gpu': gpu_metrics,
            'queue': {
                'size': queue_size,
                'processing': cache.get('processing_count', 0)
            },
            'performance': {
                'avg_response_time': avg_response_time,
                'request_count': cache.get('request_count', 0)
            }
        }

        # Save to cache for historical data
        historical = cache.get('system_metrics_history', [])
        historical.append((time.time(), metrics))
        # Keep only last 24 hours (86400 seconds)
        historical = [m for m in historical if time.time() - m[0] < 86400]
        cache.set('system_metrics_history', historical, timeout=86400)

        # Save current metrics
        cache.set(self.metrics_key, metrics, timeout=300)  # 5 min expiry

        return metrics

    def check_alerts(self, metrics):
        """Check if any metrics exceed alert thresholds"""
        alerts = []

        # Check CPU
        if metrics['cpu']['usage_percent'] > self.alert_thresholds['cpu_usage']:
            alerts.append({
                'type': 'cpu_high',
                'message': f"High CPU usage: {metrics['cpu']['usage_percent']:.1f}%",
                'severity': 'warning'
            })

        # Check Memory
        if metrics['memory']['usage_percent'] > self.alert_thresholds['memory_usage']:
            alerts.append({
                'type': 'memory_high',
                'message': f"High memory usage: {metrics['memory']['usage_percent']:.1f}%",
                'severity': 'warning'
            })

        # Check GPU
        if metrics['gpu']:
            gpu = metrics['gpu'][0]  # First GPU
            if gpu['load'] > self.alert_thresholds['gpu_usage']:
                alerts.append({
                    'type': 'gpu_high',
                    'message': f"High GPU usage: {gpu['load']:.1f}%",
                    'severity': 'warning'
                })
            if gpu['memory_percent'] > self.alert_thresholds['gpu_memory']:
                alerts.append({
                    'type': 'gpu_memory_high',
                    'message': f"High GPU memory usage: {gpu['memory_percent']:.1f}%",
                    'severity': 'warning'
                })

        # Check queue size
        if metrics['queue']['size'] > self.alert_thresholds['queue_size']:
            alerts.append({
                'type': 'queue_backlog',
                'message': f"Queue backlog: {metrics['queue']['size']} requests",
                'severity': 'warning'
            })

        # Check response time
        if metrics['performance']['avg_response_time'] > self.alert_thresholds['response_time']:
            alerts.append({
                'type': 'slow_responses',
                'message': f"Slow responses: {metrics['performance']['avg_response_time']:.2f}s avg",
                'severity': 'warning'
            })

        # Process alerts with cooldown
        for alert in alerts:
            last_alert = cache.get(f"alert:{alert['type']}")
            if not last_alert or time.time() - last_alert > self.alert_cooldown:
                self._trigger_alert(alert)
                cache.set(f"alert:{alert['type']}", time.time(), timeout=self.alert_cooldown)

        return alerts

    def _trigger_alert(self, alert):
        """Send alert notification (e.g., email, Slack, etc.)"""
        logger.warning(f"System Alert: {alert['message']}")

        # In production, you might:
        # - Send via email
        # - Push to Slack/Telegram
        # - Trigger PagerDuty
        # Example: requests.post("https://hooks.slack.com/...", json={"text": alert['message']})

    def run_monitoring(self, interval=60):
        """Run continuous monitoring"""
        logger.info("Starting system monitoring...")

        while True:
            try:
                metrics = self.collect_metrics()
                alerts = self.check_alerts(metrics)

                # Log summary
                logger.info(
                    f"Monitoring: CPU={metrics['cpu']['usage_percent']:.1f}% | "
                    f"Mem={metrics['memory']['usage_percent']:.1f}% | "
                    f"Queue={metrics['queue']['size']} | "
                    f"Resp={metrics['performance']['avg_response_time']:.2f}s"
                )

                time.sleep(interval)

            except Exception as e:
                logger.error(f"Monitoring error: {str(e)}", exc_info=True)
                time.sleep(10)  # Back off after error


# Management command for monitoring
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Run system monitoring'

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=60,
            help='Monitoring interval in seconds'
        )

    def handle(self, *args, **options):
        monitor = SystemMonitor()
        self.stdout.write(f"Starting monitoring with interval {options['interval']}s...")
        try:
            monitor.run_monitoring(interval=options['interval'])
        except KeyboardInterrupt:
            self.stdout.write("Monitoring stopped by user.")
        except Exception as e:
            self.stderr.write(f"Monitoring failed: {e}")