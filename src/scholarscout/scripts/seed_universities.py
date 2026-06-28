"""
Seed script — populates the university registry with initial data.

Run once after the initial migration:
  python -m scholarscout.scripts.seed_universities

Contains ~100 top global universities with verified domains and rankings.
"""

from __future__ import annotations

import asyncio
import logging

from scholarscout.database import get_session

logger = logging.getLogger(__name__)

# fmt: off
INITIAL_UNIVERSITIES = [
    # North America
    {"name": "Massachusetts Institute of Technology", "country": "US", "website": "https://mit.edu", "domain": "mit.edu", "ranking": 1, "timezone": "America/New_York"},
    {"name": "Stanford University", "country": "US", "website": "https://stanford.edu", "domain": "stanford.edu", "ranking": 2, "timezone": "America/Los_Angeles"},
    {"name": "Harvard University", "country": "US", "website": "https://harvard.edu", "domain": "harvard.edu", "ranking": 3, "timezone": "America/New_York"},
    {"name": "Carnegie Mellon University", "country": "US", "website": "https://cmu.edu", "domain": "cmu.edu", "ranking": 22, "timezone": "America/New_York"},
    {"name": "University of California Berkeley", "country": "US", "website": "https://berkeley.edu", "domain": "berkeley.edu", "ranking": 10, "timezone": "America/Los_Angeles"},
    {"name": "University of Toronto", "country": "CA", "website": "https://utoronto.ca", "domain": "utoronto.ca", "ranking": 21, "timezone": "America/Toronto"},
    {"name": "McGill University", "country": "CA", "website": "https://mcgill.ca", "domain": "mcgill.ca", "ranking": 31, "timezone": "America/Toronto"},
    # Europe
    {"name": "University of Cambridge", "country": "GB", "website": "https://cam.ac.uk", "domain": "cam.ac.uk", "ranking": 4, "timezone": "Europe/London"},
    {"name": "University of Oxford", "country": "GB", "website": "https://ox.ac.uk", "domain": "ox.ac.uk", "ranking": 5, "timezone": "Europe/London"},
    {"name": "ETH Zurich", "country": "CH", "website": "https://ethz.ch", "domain": "ethz.ch", "ranking": 7, "timezone": "Europe/Zurich"},
    {"name": "Technical University of Munich", "country": "DE", "website": "https://tum.de", "domain": "tum.de", "ranking": 30, "timezone": "Europe/Berlin"},
    {"name": "Delft University of Technology", "country": "NL", "website": "https://tudelft.nl", "domain": "tudelft.nl", "ranking": 47, "timezone": "Europe/Amsterdam"},
    {"name": "KTH Royal Institute of Technology", "country": "SE", "website": "https://kth.se", "domain": "kth.se", "ranking": 89, "timezone": "Europe/Stockholm"},
    {"name": "EPFL", "country": "CH", "website": "https://epfl.ch", "domain": "epfl.ch", "ranking": 12, "timezone": "Europe/Zurich"},
    # Asia-Pacific
    {"name": "National University of Singapore", "country": "SG", "website": "https://nus.edu.sg", "domain": "nus.edu.sg", "ranking": 8, "timezone": "Asia/Singapore"},
    {"name": "University of Melbourne", "country": "AU", "website": "https://unimelb.edu.au", "domain": "unimelb.edu.au", "ranking": 14, "timezone": "Australia/Melbourne"},
    {"name": "Peking University", "country": "CN", "website": "https://pku.edu.cn", "domain": "pku.edu.cn", "ranking": 17, "timezone": "Asia/Shanghai"},
    {"name": "Indian Institute of Technology Bombay", "country": "IN", "website": "https://iitb.ac.in", "domain": "iitb.ac.in", "ranking": 118, "timezone": "Asia/Kolkata"},
    {"name": "University of Tokyo", "country": "JP", "website": "https://u-tokyo.ac.jp", "domain": "u-tokyo.ac.jp", "ranking": 23, "timezone": "Asia/Tokyo"},
    # Africa / Middle East
    {"name": "University of Cape Town", "country": "ZA", "website": "https://uct.ac.za", "domain": "uct.ac.za", "ranking": 226, "timezone": "Africa/Johannesburg"},
    {"name": "American University of Beirut", "country": "LB", "website": "https://aub.edu.lb", "domain": "aub.edu.lb", "ranking": 401, "timezone": "Asia/Beirut"},
]
# fmt: on


async def seed() -> None:
    from scholarscout.contexts.university_registry.infrastructure.models import UniversityModel
    from sqlalchemy import select
    import uuid
    from datetime import UTC, datetime

    async with get_session() as session:
        for data in INITIAL_UNIVERSITIES:
            stmt = select(UniversityModel).where(UniversityModel.domain == data["domain"])
            existing = (await session.execute(stmt)).scalar_one_or_none()
            if existing:
                logger.info("Skipping existing: %s", data["domain"])
                continue

            now = datetime.now(UTC)
            model = UniversityModel(
                id=uuid.uuid4(),
                name=data["name"],
                country=data["country"],
                website=data["website"],
                domain=data["domain"],
                ranking=data.get("ranking"),
                timezone=data.get("timezone", "UTC"),
                status="active",
                crawl_frequency_hours=24,
                crawl_priority=0,
                crawl_concurrency=5,
                crawl_delay_seconds=2.0,
                crawl_discovery_depth=4,
                crawl_max_pages=500,
                crawl_use_playwright=False,
                crawl_extra_seeds=[],
                metadata_={},
                created_at=now,
                updated_at=now,
            )
            session.add(model)
            logger.info("Seeded: %s", data["name"])

    logger.info("Seeding complete. %d universities processed.", len(INITIAL_UNIVERSITIES))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(seed())
