"""
Prometheus metrics registry.

Defines all application-level metrics in one place.
Individual components import from here rather than creating their own
Counters/Histograms to avoid duplicate-registration errors.

SLI targets:
  - crawl_success_rate > 95%
  - search_latency_p99 < 100ms
  - extraction_success_rate > 90%
  - queue_depth < 10,000 (alert at 50,000)
"""

from prometheus_client import Counter, Gauge, Histogram, Info, Summary

# ── Crawler metrics ──────────────────────────────────────────────────────

crawl_requests_total = Counter(
    "scholarscout_crawl_requests_total",
    "Total crawl HTTP requests issued",
    ["university_id", "status"],
)

crawl_duration_seconds = Histogram(
    "scholarscout_crawl_duration_seconds",
    "Time to fetch a single page",
    ["university_id"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

pages_crawled_total = Counter(
    "scholarscout_pages_crawled_total",
    "Total pages successfully crawled",
    ["university_id", "page_type"],
)

crawl_errors_total = Counter(
    "scholarscout_crawl_errors_total",
    "Crawl errors by type",
    ["university_id", "error_type"],
)

crawl_queue_depth = Gauge(
    "scholarscout_crawl_queue_depth",
    "Current number of URLs in the crawl queue",
    ["priority"],
)

active_crawlers = Gauge(
    "scholarscout_active_crawlers",
    "Number of currently active crawler workers",
)

# ── Extraction metrics ────────────────────────────────────────────────────

extraction_duration_seconds = Histogram(
    "scholarscout_extraction_duration_seconds",
    "Time to extract an opportunity from a page",
    ["method"],  # rule | llm | hybrid
    buckets=[0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 30.0],
)

opportunities_extracted_total = Counter(
    "scholarscout_opportunities_extracted_total",
    "Total opportunities successfully extracted",
    ["university_id", "degree_level"],
)

extraction_errors_total = Counter(
    "scholarscout_extraction_errors_total",
    "Extraction failures by reason",
    ["reason"],
)

llm_tokens_used_total = Counter(
    "scholarscout_llm_tokens_used_total",
    "Total LLM tokens consumed",
    ["provider", "model", "direction"],  # direction: input | output
)

llm_cost_usd_total = Counter(
    "scholarscout_llm_cost_usd_total",
    "Estimated LLM cost in USD",
    ["provider", "model"],
)

# ── Search metrics ────────────────────────────────────────────────────────

search_requests_total = Counter(
    "scholarscout_search_requests_total",
    "Total search requests",
    ["query_type"],  # keyword | semantic | hybrid
)

search_latency_seconds = Histogram(
    "scholarscout_search_latency_seconds",
    "End-to-end search latency",
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)

search_results_returned = Histogram(
    "scholarscout_search_results_returned",
    "Number of results returned per search",
    buckets=[0, 1, 5, 10, 20, 50, 100],
)

# ── Catalog metrics ───────────────────────────────────────────────────────

opportunities_total = Gauge(
    "scholarscout_opportunities_total",
    "Total opportunities in catalog",
    ["status"],  # active | expired | unverified
)

opportunities_freshness_hours = Histogram(
    "scholarscout_opportunities_freshness_hours",
    "Distribution of opportunity data age",
    buckets=[1, 6, 24, 72, 168, 720],  # 1h, 6h, 1d, 3d, 1w, 1mo
)

# ── Notification metrics ──────────────────────────────────────────────────

notifications_sent_total = Counter(
    "scholarscout_notifications_sent_total",
    "Total notifications dispatched",
    ["channel", "status"],
)

notification_queue_depth = Gauge(
    "scholarscout_notification_queue_depth",
    "Notifications awaiting dispatch",
)

# ── System info ───────────────────────────────────────────────────────────

build_info = Info(
    "scholarscout_build",
    "Build information",
)
