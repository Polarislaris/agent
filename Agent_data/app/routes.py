"""
FastAPI routes — provides intern data API for Java backend
"""
import time
from typing import List
from fastapi import APIRouter, HTTPException

from app.models import (
    InternPost,
    JobDocumentCleanRequest,
    JobDocumentCleanResponse,
    JobDocumentCleanResult,
    ScrapeDataResponse,
)
from app.jd_cleaner import clean_document
from app.scraper import fetch_intern_posts, scrape_for_db_sync
import app.scraper as _scraper_module

router = APIRouter(prefix="/api/v1", tags=["interns"])


# GET /api/v1/interns
@router.get("/interns", response_model=List[InternPost], summary="Get all intern posts")
async def list_interns():
    """Return all intern posts (scraper handles 24h caching)"""
    return await fetch_intern_posts()


# GET /api/v1/interns/{id}
@router.get("/interns/{post_id}", response_model=InternPost, summary="Get single intern post")
async def get_intern(post_id: str):
    """Return single intern post by ID"""
    posts = await fetch_intern_posts()
    for p in posts:
        if p.id == post_id:
            return p
    raise HTTPException(status_code=404, detail=f"Intern post '{post_id}' not found")


# POST /api/v1/interns/refresh
@router.post("/interns/refresh", response_model=dict, summary="Refresh data cache")
async def refresh_cache():
    """Force re-scrape bypassing 24h cache"""
    posts = await fetch_intern_posts(force=True)
    return {"status": "ok", "count": len(posts)}


# GET /api/v1/cache/status
@router.get("/cache/status", response_model=dict, summary="View cache status and preview")
async def cache_status(limit: int = 10):
    """
    返回当前内存缓存的状态信息：
    - count       : 缓存中的 post 数量
    - cache_age_min : 缓存年龄（分钟）；-1 表示尚未填充
    - ttl_min     : 缓存剩余有效时间（分钟）
    - posts       : 前 limit 条缓存记录（默认 10 条）
    """
    cache_data = _scraper_module._cache_data
    cache_ts = _scraper_module._cache_timestamp
    ttl = _scraper_module._CACHE_TTL_SECONDS

    now = time.time()
    if cache_ts == 0.0:
        age_min = -1
        ttl_remaining_min = 0
    else:
        age_min = round((now - cache_ts) / 60, 1)
        ttl_remaining_min = round(max(ttl - (now - cache_ts), 0) / 60, 1)

    # Check enrichment status
    enrichment_running = _scraper_module._enrichment_running
    enriched_count = sum(1 for p in cache_data if p.description or p.fitScore)

    preview = [p.dict() for p in cache_data[:limit]]

    return {
        "count": len(cache_data),
        "cache_age_min": age_min,
        "ttl_remaining_min": ttl_remaining_min,
        "enrichment_running": enrichment_running,
        "enriched_count": enriched_count,
        "posts": preview,
    }


# POST /api/v1/scrape-data — scrape README + apply pages (≤15d), return DB-ready data
@router.post("/scrape-data", response_model=ScrapeDataResponse, summary="Scrape and return DB-ready data")
def scrape_data():
    """
    Scrape SimplifyJobs README + apply pages (listings ≤15 days old, latest 200).
    使用同步 def，FastAPI 自动放入线程池，不阻塞 event loop。
    Returns structured data for Java backend to write into Supabase.
    """
    result = scrape_for_db_sync()
    return result


# POST /api/v1/clean-job-documents — clean raw JD text for Java to write back DB
@router.post(
    "/clean-job-documents",
    response_model=JobDocumentCleanResponse,
    summary="Clean job_documents raw text",
)
def clean_job_documents(payload: JobDocumentCleanRequest):
    """
    Receive raw JD texts from Java, clean them in Python, and return results.
    Java is responsible for DB write-back (update/delete).
    """
    min_length = payload.min_length if payload.min_length and payload.min_length > 0 else 50

    results: List[JobDocumentCleanResult] = []
    for doc in payload.documents:
        cleaned = clean_document(doc.job_id, doc.jd_raw_text or "", min_length)
        results.append(JobDocumentCleanResult(**cleaned))

    delete_count = sum(1 for r in results if r.delete_row)
    keep_count = len(results) - delete_count

    return JobDocumentCleanResponse(
        results=results,
        total=len(results),
        keep_count=keep_count,
        delete_count=delete_count,
    )



