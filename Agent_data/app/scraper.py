"""
Scraper — fetches intern posts from SimplifyJobs GitHub, LinkedIn, Indeed.
Parses the Summer2026-Internships README table, filters to last 15 days,
and enriches with AI analysis.
"""
import concurrent.futures
import json
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

# Apply-page scraping config
_APPLY_PAGE_TIMEOUT = 15          # seconds per request
_MAX_SCRAPE_WORKERS = 10           # concurrent threads


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
# Apply-page scraper — fetch job description from apply link
###############################################################################

_SCRAPE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}

# CSS selectors ordered by specificity — first match with enough text wins
_JD_SELECTORS = [
    "[class*='job-description']",
    "[class*='jobDescription']",
    "[class*='job_description']",
    "[class*='description']",
    "[id*='job-description']",
    "[id*='jobDescription']",
    "[data-testid*='description']",
    "article",
    "[role='main']",
    "main",
    ".content",
    "#content",
]


def _scrape_single_apply_page(url: str) -> Dict[str, str]:
    """Fetch one apply-page URL and return job description text + scrape method.

    Tries ALL four extraction strategies, keeps the one with the longest text.

    Strategies:
    1. <meta name/property="description" | "og:description">
    2. <script type="application/ld+json"> structured data
    3. CSS selectors targeting job description containers
    4. <body> text fallback

    Returns dict with keys: text, method, fetch_url
    """
    if not url or url == "#":
        return {"text": "", "method": "", "fetch_url": ""}

    # Normalise Workable: /apply → / (the listing page has richer meta)
    clean_url = re.sub(r"/apply/?(\?.*)?$", r"/\1", url)

    try:
        resp = requests.get(
            clean_url, headers=_SCRAPE_HEADERS,
            timeout=_APPLY_PAGE_TIMEOUT, allow_redirects=True,
        )
        resp.raise_for_status()
    except Exception as e:
        logger.debug("Failed to fetch apply page %s: %s", clean_url, e)
        return {"text": "", "method": "", "fetch_url": clean_url}

    actual_url = resp.url if resp.url else clean_url
    soup = BeautifulSoup(resp.text, "html.parser")

    # Collect all candidates: (text, method)
    candidates: List[tuple] = []

    # --- Strategy 1: meta description / og:description ---
    meta_text = ""
    for meta in soup.find_all("meta"):
        attr = meta.get("name", "") or meta.get("property", "")
        if attr.lower() in ("description", "og:description", "twitter:description"):
            content = (meta.get("content") or "").strip()
            if len(content) > len(meta_text):
                meta_text = content
    if meta_text:
        candidates.append((meta_text, "meta"))

    # --- Strategy 2: ld+json structured data ---
    ldjson_text = ""
    for s in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(s.string)
            if isinstance(data, dict):
                desc = data.get("description", "")
                if isinstance(desc, str) and len(desc) > len(ldjson_text):
                    ldjson_text = desc
        except Exception:
            pass
    if ldjson_text:
        cleaned_ldjson = BeautifulSoup(ldjson_text, "html.parser").get_text(strip=True)
        candidates.append((cleaned_ldjson, "ld+json"))

    # --- Strategy 3: CSS selectors ---
    # Work on a copy to avoid mutating soup for body fallback
    soup_clean = BeautifulSoup(str(soup), "html.parser")
    for tag in soup_clean(["script", "style", "nav", "footer", "header", "noscript", "iframe"]):
        tag.decompose()

    for selector in _JD_SELECTORS:
        el = soup_clean.select_one(selector)
        if el:
            candidate = el.get_text(separator="\n", strip=True)
            if len(candidate) >= 50:
                candidate = re.sub(r"\n{3,}", "\n\n", candidate).strip()
                candidates.append((candidate, f"css:{selector}"))
                break  # best CSS match

    # --- Strategy 4: <body> fallback ---
    body = soup_clean.find("body")
    if body:
        body_text = body.get_text(separator="\n", strip=True)
        body_text = re.sub(r"\n{3,}", "\n\n", body_text).strip()
        if body_text:
            candidates.append((body_text, "body"))

    # --- Pick the longest candidate ---
    if not candidates:
        return {"text": "", "method": "", "fetch_url": actual_url}

    best_text, best_method = max(candidates, key=lambda c: len(c[0]))
    return {"text": best_text, "method": best_method, "fetch_url": actual_url}


def scrape_apply_pages(raw_posts: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Concurrently scrape all apply page URLs.
    Returns a list of dicts with keys: text, method, fetch_url (same length as raw_posts).
    """
    urls = [p.get("applyLink", "") for p in raw_posts]
    empty_result = {"text": "", "method": "", "fetch_url": ""}
    results: List[Dict[str, str]] = [dict(empty_result) for _ in urls]

    logger.info("Scraping %d apply pages for job descriptions...", len(urls))
    with concurrent.futures.ThreadPoolExecutor(max_workers=_MAX_SCRAPE_WORKERS) as pool:
        future_map = {
            pool.submit(_scrape_single_apply_page, url): idx
            for idx, url in enumerate(urls)
            if url and url != "#"
        }
        done = 0
        for future in concurrent.futures.as_completed(future_map):
            idx = future_map[future]
            done += 1
            try:
                results[idx] = future.result()
            except Exception as e:
                logger.debug("Apply page scrape error idx %d: %s", idx, e)
            if done % 20 == 0:
                logger.info("Apply page progress: %d/%d", done, len(future_map))

    ok = sum(1 for r in results if r["text"])
    logger.info("Scraped %d/%d apply pages successfully", ok, len(urls))
    return results


###############################################################################
# Core — scrape SimplifyJobs GitHub README
###############################################################################

async def scrape_simplify(limit: int = 200) -> List[InternPost]:
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

    # Keep newest listings first before applying limit
    unique_posts.sort(key=lambda p: p.get("date", ""), reverse=True)

    # Limit
    if len(unique_posts) > limit:
        unique_posts = unique_posts[:limit]

    # Build InternPost objects immediately (without AI enrichment)
    posts: List[InternPost] = []
    for raw in unique_posts:
        post_id = generate_id(raw["title"], raw["company"], raw.get("location", ""))
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
    """
    Background thread: scrape apply pages → feed job descriptions to AI → update cache.
    The API returns instantly with basic data; AI fields populate later.
    """
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
            # ── Step 1: scrape apply pages for job descriptions ────────
            logger.info("Step 1/2: scraping apply pages for %d posts...", len(raw_posts))
            jd_results = scrape_apply_pages(raw_posts)

            # Attach jobDescription to raw_posts for AI consumption
            enriched_raw: List[Dict[str, str]] = []
            for raw, jd_info in zip(raw_posts, jd_results):
                entry = dict(raw)
                entry["jobDescription"] = jd_info["text"]
                enriched_raw.append(entry)

            # ── Step 2: call AI with job descriptions ──────────────────
            logger.info("Step 2/2: calling AI enrichment for %d posts...", len(enriched_raw))
            enrichments = enrich_posts(enriched_raw)

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
            logger.info("Background enrichment completed for %d posts (%d with JD)",
                        len(posts), sum(1 for r in jd_results if r["text"]))
        except Exception as e:
            logger.error("Background enrichment failed: %s", e)
        finally:
            with _enrichment_lock:
                _enrichment_running = False

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()


###############################################################################
# scrape_for_db — returns structured data for Java backend to write to DB
###############################################################################

def scrape_for_db_sync(limit: int = 200) -> Dict[str, Any]:
    """
    同步版本的 scrape_for_db，供 FastAPI 线程池（def 路由）直接调用，不阻塞 event loop。
    Scrape README + apply pages, return structured data for DB insertion.
    Returns:
        {
          "jobs": [ {job_id, company, title, location, apply_url, post_date} ],
          "job_documents": [ {job_id, fetch_url, scrape_method, jd_raw_text} ]
        }
    """
    logger.info("scrape_for_db: Fetching SimplifyJobs README from GitHub...")
    try:
        resp = requests.get(_SIMPLIFY_README_URL, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        logger.error("Failed to fetch SimplifyJobs README: %s", e)
        return {"jobs": [], "job_documents": []}

    readme_text = resp.text
    logger.info("README fetched (%d bytes), parsing HTML tables...", len(readme_text))

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

            company_cell = cells[0].get_text(strip=True)
            title = cells[1].get_text(strip=True)
            location = cells[2].get_text(separator=", ", strip=True)
            apply_html = str(cells[3])
            age_str = cells[4].get_text(strip=True)

            if "🔒" in company_cell or "🔒" in title:
                continue

            age_days = _parse_age(age_str)
            if age_days is None or age_days > _MAX_AGE_DAYS:
                continue

            # ↳ 子列表行 → 直接丢弃（公司名不明确，不发送给 Java）
            if company_cell.strip().startswith("↳") or company_cell.strip() == "↳":
                logger.debug("Discarding sub-listing (↳): %s", title)
                continue

            clean_name = _clean_company(company_cell)
            if not clean_name:
                clean_name = last_company
            else:
                last_company = clean_name

            title = re.sub(r"\s*🎓\s*$", "", title).strip()
            apply_link = _extract_apply_url(apply_html)
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

    # Keep newest listings first before applying limit
    unique_posts.sort(key=lambda p: p.get("date", ""), reverse=True)

    if len(unique_posts) > limit:
        unique_posts = unique_posts[:limit]

    # Scrape apply pages for JD
    logger.info("Scraping apply pages for %d posts...", len(unique_posts))
    jd_results = scrape_apply_pages(unique_posts)

    # Build DB-ready structures — discard any job where JD could not be scraped
    jobs: List[Dict[str, Any]] = []
    job_documents: List[Dict[str, Any]] = []
    discarded = 0

    for raw, jd_info in zip(unique_posts, jd_results):
        jd_text = jd_info.get("text", "").strip()
        if not jd_text:
            discarded += 1
            logger.debug("Discarding %s @ %s — no raw JD scraped", raw["title"], raw["company"])
            continue

        job_id = generate_id(raw["title"], raw["company"], raw.get("location", ""))
        company = (raw.get("company") or "").strip()
        title = (raw.get("title") or "").strip()
        apply_url = (raw.get("applyLink") or "").strip()
        post_date = (raw.get("date") or "").strip()
        fetch_url = (jd_info.get("fetch_url") or "").strip()
        scrape_method = (jd_info.get("method") or "").strip()

        # Jobs 表校验：job_id / company / title / apply_url / post_date 不可为空（location 可以为空）
        if not job_id or not company or not title or not apply_url or not post_date:
            discarded += 1
            logger.info(
                "Discarding job (null fields): job_id=%s company=%s title=%s apply_url=%s post_date=%s",
                bool(job_id), bool(company), bool(title), bool(apply_url), bool(post_date),
            )
            continue

        # job_documents 表校验：fetch_url / scrape_method / jd_raw_text 不可为空
        if not fetch_url or not scrape_method:
            discarded += 1
            logger.info(
                "Discarding job %s (document null fields): fetch_url=%s scrape_method=%s",
                job_id, bool(fetch_url), bool(scrape_method),
            )
            continue

        jobs.append({
            "job_id": job_id,
            "company": company,
            "title": title,
            "location": raw.get("location", ""),
            "apply_url": apply_url,
            "post_date": post_date,
        })

        job_documents.append({
            "job_id": job_id,
            "fetch_url": fetch_url,
            "scrape_method": scrape_method,
            "jd_raw_text": jd_text,
        })

    logger.info(
        "scrape_for_db: %d jobs kept, %d discarded (no JD / null fields), %d job_documents",
        len(jobs), discarded, len(job_documents),
    )
    return {"jobs": jobs, "job_documents": job_documents}


async def scrape_for_db(limit: int = 200) -> Dict[str, Any]:
    """async 包装，兼容老代码调用。内部直接调用同步版本。"""
    return scrape_for_db_sync(limit)





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
