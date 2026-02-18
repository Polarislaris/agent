"""
FastAPI app entrypoint
Port: 8000
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import router

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-7s  %(name)s — %(message)s")

app = FastAPI(
    title="Agent Data Service",
    description="Python data scraper service — provides intern job records as JSON for Java backend",
    version="0.1.0",
)

    # CORS (allow Java backend & frontend local dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok"}
