"""
FastAPI routes — provides intern data API for Java backend
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException

from app.models import InternPost
from app.scraper import fetch_intern_posts

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
