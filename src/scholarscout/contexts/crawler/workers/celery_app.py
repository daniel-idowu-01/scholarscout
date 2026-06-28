"""
Celery application configuration.

All contexts share one Celery app instance (modular monolith).
When a context is extracted into its own service, it gets its
own Celery app with the same broker/backend config.

Queue design:
  crawl.high      → new universities, user-triggered crawls
  crawl.normal    → scheduled refreshes
  crawl.low       → background discovery
  extraction.high → newly discovered opportunities
  extraction.normal → re-extraction on content change
  notifications   → outbound notifications

Priorities within a queue: Celery uses AMQP priority (0–9) on RabbitMQ
or a score-based approach on Redis via sorted sets.
"""

from __future__ import annotations

from celery import Celery
from celery.schedules import crontab
from kombu import Queue

from scholarscout.config import settings

app = Celery("scholarscout")

app.config_from_object(
    {
        "broker_url": settings.redis.celery_url,
        "result_backend": settings.redis.celery_url,
        "task_serializer": "json",
        "result_serializer": "json",
        "accept_content": ["json"],
        "timezone": "UTC",
        "enable_utc": True,
        "task_track_started": True,
        "task_time_limit": 3600,
        "task_soft_time_limit": 3300,
        "worker_prefetch_multiplier": 1,
        "worker_max_tasks_per_child": 500,
        "task_acks_late": True,  # Only ack after task completes (safer)
        "task_reject_on_worker_lost": True,
        "task_routes": {
            "scholarscout.contexts.crawler.workers.crawl_tasks.crawl_url": {
                "queue": "crawl.normal"
            },
            "scholarscout.contexts.crawler.workers.crawl_tasks.crawl_url_high": {
                "queue": "crawl.high"
            },
            "scholarscout.contexts.crawler.workers.crawl_tasks.discover_university": {
                "queue": "crawl.low"
            },
            "scholarscout.contexts.extraction.workers.extraction_tasks.extract_page": {
                "queue": "extraction.normal"
            },
            "scholarscout.contexts.extraction.workers.extraction_tasks.extract_page_high": {
                "queue": "extraction.high"
            },
            "scholarscout.contexts.notifications.workers.notification_tasks.send_notification": {
                "queue": "notifications"
            },
        },
        "task_queues": (
            Queue("crawl.high", routing_key="crawl.high"),
            Queue("crawl.normal", routing_key="crawl.normal"),
            Queue("crawl.low", routing_key="crawl.low"),
            Queue("extraction.high", routing_key="extraction.high"),
            Queue("extraction.normal", routing_key="extraction.normal"),
            Queue("notifications", routing_key="notifications"),
        ),
        "beat_schedule": {
            # ── Crawl scheduler: every 5 min, picks up universities due for crawl
            "schedule-pending-crawls": {
                "task": "scholarscout.contexts.crawler.workers.scheduler.schedule_pending_crawls",
                "schedule": crontab(minute="*/5"),
                "options": {"queue": "crawl.low"},
            },
            # ── Verify active opportunities daily
            "verify-active-opportunities": {
                "task": "scholarscout.contexts.catalog.workers.catalog_tasks.verify_active_opportunities",
                "schedule": crontab(hour="2", minute="0"),
                "options": {"queue": "crawl.low"},
            },
            # ── Digest notifications
            "send-daily-digests": {
                "task": "scholarscout.contexts.notifications.workers.notification_tasks.send_digests",
                "schedule": crontab(hour="8", minute="0"),
                "kwargs": {"frequency": "daily"},
                "options": {"queue": "notifications"},
            },
            "send-weekly-digests": {
                "task": "scholarscout.contexts.notifications.workers.notification_tasks.send_digests",
                "schedule": crontab(hour="9", minute="0", day_of_week="monday"),
                "kwargs": {"frequency": "weekly"},
                "options": {"queue": "notifications"},
            },
            # ── Index maintenance
            "refresh-search-indexes": {
                "task": "scholarscout.contexts.search.workers.index_tasks.refresh_indexes",
                "schedule": crontab(hour="3", minute="0"),
                "options": {"queue": "crawl.low"},
            },
        },
    }
)

# Auto-discover tasks from all contexts
app.autodiscover_tasks(
    [
        "scholarscout.contexts.crawler.workers",
        "scholarscout.contexts.extraction.workers",
        "scholarscout.contexts.catalog.workers",
        "scholarscout.contexts.notifications.workers",
        "scholarscout.contexts.search.workers",
    ]
)
