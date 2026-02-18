"""
Scraper — fetches intern posts from SimplifyJobs GitHub, LinkedIn, Indeed.
Parses the Summer2026-Internships README table, filters to last 15 days,
and enriches with AI analysis.
"""
import logging
import re
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from app.models import InternPost, CompanyInfo
from app.utils import generate_id, truncate
from app.ai_analyzer import enrich_posts

logger = logging.getLogger(__name__)

# GitHub raw URL for the SimplifyJobs README
_SIMPLIFY_README_URL = (
    "https://raw.githubusercontent.com/SimplifyJobs/Summer2026-Internships/dev/README.md"
)

# Cache: daily refresh
_cache_data: List[InternPost] = []
_cache_timestamp: float = 0.0
_CACHE_TTL_SECONDS = 86400  # 24 hours

# Max age in days to keep a listing
_MAX_AGE_DAYS = 15

# Max description length
_MAX_DESC_LEN = 300


###############################################################################
# Helper — parse age string to days
###############################################################################

def _parse_age(age_str: str) -> Optional[int]:
    """Convert age string like '0d', '3d', '1mo' to integer days."""
    age_str = age_str.strip().lower()
    m = re.match(r"^(\d+)\s*d$", age_str)
    if m:
        return int(m.group(1))
    m = re.match(r"^(\d+)\s*mo$", age_str)
    if m:
        return int(m.group(1)) * 30
    return None


###############################################################################
# Helper — extract first apply URL from HTML cell
###############################################################################

def _extract_apply_url(td_html: str) -> str:
    """Extract the first <a href=...> whose alt='Apply' from the Application cell."""
    soup = BeautifulSoup(td_html, "html.parser")
    # Prefer the direct Apply link (not Simplify redirect)
    for a_tag in soup.find_all("a", href=True):
        img = a_tag.find("img")
        if img and img.get("alt") == "Apply":
            return a_tag["href"]
    # Fallback: any link
    first_a = soup.find("a", href=True)
    return first_a["href"] if first_a else ""


###############################################################################
# Helper — clean company name
###############################################################################

def _clean_company(raw: str) -> str:
    """Strip emoji prefixes (🔥, 🛂, ↳) and HTML, return plain company name."""
    # Remove known emoji prefixes
    cleaned = re.sub(r"^[🔥🛂🇺🇸🎓\s]+", "", raw).strip()
    # Remove ↳ (sub-listing indicator)
    cleaned = cleaned.replace("↳", "").strip()
    return cleaned


###############################################################################
# Core — scrape SimplifyJobs GitHub README
###############################################################################

async def scrape_simplify(limit: int = 100) -> List[InternPost]:
    """
    Scrape the SimplifyJobs Summer2026-Internships GitHub README.
    - Fetches the raw markdown (contains HTML tables)
    - Parses each <table> section for intern listings
    - Filters to listings ≤ 15 days old
    - Enriches with AI analysis (description, requirements, etc.)
    """
    logger.info("Fetching SimplifyJobs README from GitHub...")
    try:
        resp = requests.get(_SIMPLIFY_README_URL, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        logger.error("Failed to fetch SimplifyJobs README: %s", e)
        return []

    readme_text = resp.text
    logger.info("README fetched (%d bytes), parsing HTML tables...", len(readme_text))

    # The README embeds <table>...</table> blocks — extract and parse them all
    raw_posts: List[Dict[str, str]] = []
    last_company = ""

    table_pattern = re.compile(r"<table>.*?</table>", re.DOTALL)
    tables = table_pattern.findall(readme_text)
    logger.info("Found %d HTML tables in README", len(tables))

    today = datetime.now()

    for table_html in tables:
        soup = BeautifulSoup(table_html, "html.parser")
        rows = soup.find_all("tr")

        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 5:
                continue

            # Columns: Company | Role | Location | Application | Age
            company_cell = cells[0].get_text(strip=True)
            title = cells[1].get_text(strip=True)
            location = cells[2].get_text(separator=", ", strip=True)
            apply_html = str(cells[3])
            age_str = cells[4].get_text(strip=True)

            # Skip closed listings (🔒)
            if "🔒" in company_cell or "🔒" in title:
                continue

            # Parse age
            age_days = _parse_age(age_str)
            if age_days is None or age_days > _MAX_AGE_DAYS:
                continue

            # Resolve company name (↳ means same company as previous row)
            clean_name = _clean_company(company_cell)
            if clean_name == "" or company_cell.strip().startswith("↳"):
                clean_name = last_company
            else:
                last_company = clean_name

            # Clean title (remove emoji suffixes like 🎓)
            title = re.sub(r"\s*🎓\s*$", "", title).strip()

            # Apply link
            apply_link = _extract_apply_url(apply_html)

            # Compute date from age
            post_date = (today - timedelta(days=age_days)).strftime("%Y-%m-%d")

            raw_posts.append({
                "company": clean_name,
                "title": title,
                "location": location,
                "applyLink": apply_link,
                "date": post_date,
            })

    logger.info("Parsed %d listings within %d-day window", len(raw_posts), _MAX_AGE_DAYS)

    # De-duplicate by (company + title + location)
    seen = set()
    unique_posts: List[Dict[str, str]] = []
    for p in raw_posts:
        key = f"{p['company']}|{p['title']}|{p['location']}"
        if key not in seen:
            seen.add(key)
            unique_posts.append(p)
    logger.info("After dedup: %d unique listings", len(unique_posts))

    # Limit
    if len(unique_posts) > limit:
        unique_posts = unique_posts[:limit]

    # Build InternPost objects immediately (without AI enrichment)
    posts: List[InternPost] = []
    for raw in unique_posts:
        post_id = generate_id(raw["title"], raw["company"])
        posts.append(InternPost(
            id=post_id,
            title=raw["title"],
            company=raw["company"],
            base=raw["location"],
            date=raw["date"],
            description="",
            requirements=[],
            applyLink=raw.get("applyLink", ""),
            companyInfo=CompanyInfo(size="", founded="", business=""),
            fitScore="",
            difficulty="",
            avgSalary="",
        ))

    logger.info("Built %d InternPost objects (AI enrichment pending)", len(posts))

    # Start AI enrichment in background thread (non-blocking)
    _start_background_enrichment(unique_posts, posts)

    return posts


# Background enrichment state
_enrichment_lock = threading.Lock()
_enrichment_running = False


def _start_background_enrichment(
    raw_posts: List[Dict[str, str]], posts: List[InternPost]
) -> None:
    """Run AI enrichment in a background thread so the API returns instantly."""
    global _enrichment_running, _cache_data

    from app.ai_analyzer import _api_key_is_set
    if not _api_key_is_set():
        logger.info("No AI API key — skipping background enrichment")
        return

    with _enrichment_lock:
        if _enrichment_running:
            logger.info("Background enrichment already running, skipping")
            return
        _enrichment_running = True

    def _run():
        global _enrichment_running, _cache_data
        try:
            logger.info("Background AI enrichment started for %d posts...", len(raw_posts))
            enrichments = enrich_posts(raw_posts)
            # Update existing post objects in-place
            for post, enriched in zip(posts, enrichments):
                post.description = truncate(enriched.get("description", ""), _MAX_DESC_LEN)
                reqs = enriched.get("requirements", [])
                post.requirements = reqs if isinstance(reqs, list) else []
                post.companyInfo = CompanyInfo(
                    size=enriched.get("companySize", ""),
                    founded=enriched.get("companyFounded", ""),
                    business=enriched.get("companyBusiness", ""),
                )
                post.fitScore = enriched.get("fitScore", "")
                post.difficulty = enriched.get("difficulty", "")
                post.avgSalary = enriched.get("avgSalary", "")
            # Update cache reference
            _cache_data = posts
            logger.info("Background AI enrichment completed for %d posts", len(posts))
        except Exception as e:
            logger.error("Background enrichment failed: %s", e)
        finally:
            with _enrichment_lock:
                _enrichment_running = False

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()


###############################################################################
# Stub scrapers — kept for future use
###############################################################################

async def scrape_linkedin(limit: int = 20) -> List[InternPost]:
    """
    TODO: Scrape LinkedIn intern jobs
    1. Build search URL: https://www.linkedin.com/jobs/search/?keywords=internship
    2. Fetch list page (requests/aiohttp)
    3. Parse job cards (BeautifulSoup):
       - Title (.base-search-card__title)
       - Company (.base-search-card__subtitle)
       - Location (.job-search-card__location)
       - Link (.base-card__full-link)
    4. Visit detail page for description/requirements
    5. Assemble as InternPost
    Note: LinkedIn has anti-bot, may need proxy/login
    """
    logger.info("LinkedIn scraper not yet implemented, returning []")
    return []


async def scrape_indeed(limit: int = 20) -> List[InternPost]:
    """
    TODO: Scrape Indeed intern jobs
    1. Search URL: https://www.indeed.com/jobs?q=internship&l=United+States
    2. Parse search results
    3. Extract job details
    """
    logger.info("Indeed scraper not yet implemented, returning []")
    return []


###############################################################################
# Unified fetch entry — with daily cache
###############################################################################

async def fetch_intern_posts(force: bool = False) -> List[InternPost]:
    """
    Unified fetch entry with 24-hour cache.
    - Scrapes SimplifyJobs GitHub (primary source)
    - Caches results for 24 hours (daily refresh)
    - Returns cached data if within TTL
    - Set force=True to bypass cache (manual refresh)
    """
    global _cache_data, _cache_timestamp

    now = time.time()
    if not force and _cache_data and (now - _cache_timestamp) < _CACHE_TTL_SECONDS:
        logger.info("Returning cached data (%d posts, age %.0f min)",
                     len(_cache_data), (now - _cache_timestamp) / 60)
        return _cache_data

    logger.info("Cache expired or empty — refreshing from SimplifyJobs GitHub...")
    posts = await scrape_simplify()

    if posts:
        _cache_data = posts
        _cache_timestamp = now
        logger.info("Cache updated with %d posts", len(posts))
    else:
        logger.warning("Scrape returned 0 posts — keeping stale cache if available")
        if not _cache_data:
            _cache_data = []
            _cache_timestamp = now

    return _cache_data
