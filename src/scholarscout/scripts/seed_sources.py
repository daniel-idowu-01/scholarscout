"""
Seed script — registers the scholarship aggregator sites we crawl.

Run after migrations:
  python -m scholarscout.scripts.seed_sources

Aggregators are stored as rows in the `universities` table with
metadata.source_type = "aggregator" so the existing crawl → extraction →
catalog pipeline (all keyed on university_id) works unchanged. Discovery for
these rows crawls the listed hub pages and follows links to individual posts
instead of guessing university paths.

By default this also pauses every non-aggregator university so crawling is
restricted to these sources. Pass --keep-universities to leave them as-is.
Re-running is safe: existing sources get their config updated.
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from scholarscout.database import get_session

logger = logging.getLogger(__name__)

# "ZZ" = unknown/international (ISO 3166 user-assigned); the host institution
# of each opportunity comes from the post content, not the aggregator.
# fmt: off
AGGREGATOR_SOURCES = [
    {"name": "Scholarships365", "domain": "scholarships365.info", "website": "https://scholarships365.info",
     "hubs": ["https://scholarships365.info/scholarships/", "https://scholarships365.info/masters-scholarships/",
              "https://scholarships365.info/phd-scholarships/", "https://scholarships365.info/fellowships/"]},
    {"name": "Opportunity Desk", "domain": "opportunitydesk.org", "website": "https://opportunitydesk.org",
     "hubs": ["https://opportunitydesk.org/category/fellowships-and-scholarships/",
              "https://opportunitydesk.org/category/fellowships-and-scholarships/masters-postgraduate/",
              "https://opportunitydesk.org/category/fellowships-and-scholarships/phd-post-doctoral/"]},
    {"name": "Scholars4Dev", "domain": "scholars4dev.com", "website": "https://www.scholars4dev.com",
     "hubs": ["https://www.scholars4dev.com/category/country/europe-scholarships/",
              "https://www.scholars4dev.com/category/country/usa-scholarships/",
              "https://www.scholars4dev.com/category/country/canada-scholarships/",
              "https://www.scholars4dev.com/category/country/australia-scholarships/"]},
    {"name": "Scholarship Positions", "domain": "scholarship-positions.com", "website": "https://scholarship-positions.com",
     "hubs": [], "status": "paused",
     "pause_reason": "Domain 301-redirects to cloudflare.vc (checked 2026-09-24); verify before enabling"},
    {"name": "After School Africa", "domain": "afterschoolafrica.com", "website": "https://www.afterschoolafrica.com",
     "hubs": ["https://www.afterschoolafrica.com/scholarship/", "https://www.afterschoolafrica.com/fellowships/",
              "https://www.afterschoolafrica.com/research-grants/"]},
    {"name": "Opportunities For Africans", "domain": "opportunitiesforafricans.com",
     "website": "https://www.opportunitiesforafricans.com", "hubs": []},
    {"name": "World Scholarship Forum", "domain": "worldscholarshipforum.com", "website": "https://worldscholarshipforum.com",
     "hubs": [], "use_playwright": True, "status": "paused",
     "pause_reason": "Returns 403 bot challenge to plain HTTP (checked 2026-09-24); needs Playwright verification"},
    {"name": "ScholarshipsAds", "domain": "scholarshipsads.com", "website": "https://www.scholarshipsads.com",
     "hubs": ["https://www.scholarshipsads.com/latest-scholarships/", "https://www.scholarshipsads.com/fully-funded-scholarships",
              "https://www.scholarshipsads.com/masters-scholarships", "https://www.scholarshipsads.com/phd-scholarships"]},
    {"name": "ScholarIdea", "domain": "scholaridea.com", "website": "https://scholaridea.com",
     "hubs": ["https://scholaridea.com/category/phd-scholarships/", "https://scholaridea.com/category/postdoctoral-scholarships/"]},
    {"name": "Scholarship Roar", "domain": "scholarshiproar.com", "website": "https://scholarshiproar.com",
     "hubs": ["https://scholarshiproar.com/category/scholarships/", "https://scholarshiproar.com/category/scholarship-lists/"]},
    {"name": "Youth Opportunities", "domain": "youthop.com", "website": "https://www.youthop.com",
     "hubs": [], "use_playwright": True},
    {"name": "Opportunities Corners", "domain": "opportunitiescorners.com", "website": "https://opportunitiescorners.com",
     "hubs": []},
]
# fmt: on


async def seed(keep_universities: bool = False) -> None:
    from scholarscout.contexts.university_registry.infrastructure.models import UniversityModel
    from sqlalchemy import select
    import uuid
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    async with get_session() as session:
        for data in AGGREGATOR_SOURCES:
            status = data.get("status", "active")
            metadata = {"source_type": "aggregator"}
            if data.get("pause_reason"):
                metadata["pause_reason"] = data["pause_reason"]

            stmt = select(UniversityModel).where(UniversityModel.domain == data["domain"])
            model = (await session.execute(stmt)).scalar_one_or_none()
            if model is None:
                model = UniversityModel(
                    id=uuid.uuid4(),
                    domain=data["domain"],
                    country="ZZ",
                    timezone="UTC",
                    crawl_concurrency=2,
                    crawl_discovery_depth=1,
                    crawl_max_pages=2000,
                    created_at=now,
                )
                session.add(model)
                logger.info("Seeded: %s", data["name"])
            else:
                logger.info("Updated: %s", data["name"])

            model.name = data["name"]
            model.website = data["website"]
            model.status = status
            model.crawl_frequency_hours = 6
            model.crawl_priority = 90
            model.crawl_delay_seconds = 3.0
            model.crawl_use_playwright = data.get("use_playwright", False)
            model.crawl_extra_seeds = data["hubs"]
            model.metadata_ = {**(model.metadata_ or {}), **metadata}
            if status == "active":
                model.metadata_.pop("pause_reason", None)
            model.updated_at = now

        if not keep_universities:
            stmt = select(UniversityModel).where(UniversityModel.status == "active")
            paused = 0
            for uni in (await session.execute(stmt)).scalars():
                if (uni.metadata_ or {}).get("source_type") == "aggregator":
                    continue
                uni.status = "paused"
                uni.metadata_ = {**(uni.metadata_ or {}), "pause_reason": "replaced by aggregator sources"}
                uni.updated_at = now
                paused += 1
            logger.info("Paused %d university sources", paused)

    logger.info("Seeding complete. %d aggregator sources processed.", len(AGGREGATOR_SOURCES))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--keep-universities",
        action="store_true",
        help="Don't pause existing university sources",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    asyncio.run(seed(keep_universities=args.keep_universities))
