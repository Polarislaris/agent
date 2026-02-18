"""
AI Analyzer — enriches raw scraped intern data with AI-generated insights.

Uses DeepSeek API (deepseek-reasoner) with JSON Output mode to produce:
  - description, requirements, companyInfo, fitScore, difficulty, avgSalary

Set your DeepSeek API key in AI_API_KEY below (or via env var DEEPSEEK_API_KEY).
DeepSeek API docs: https://api-docs.deepseek.com/
"""
import json
import logging
import os
from typing import Any, Dict, List

from openai import OpenAI

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────
# ⬇⬇⬇  推荐通过环境变量或.env文件设置DEEPSEEK_API_KEY，避免硬编码敏感信息  ⬇⬇⬇
AI_API_KEY: str = os.getenv("DEEPSEEK_API_KEY")
# ⬆⬆⬆  ─────────────────────────────────────────────────────────────  ⬆⬆⬆

# deepseek-reasoner: thinking mode of DeepSeek-V3.2, supports JSON Output
# Note: temperature / top_p / presence_penalty are NOT supported by this model
AI_MODEL: str = "deepseek-reasoner"

# Maximum posts to send per API call (keep batches small to stay within token limits)
_BATCH_SIZE = 5

# max_tokens for output (reasoning CoT + JSON answer); 8192 is safe for small batches
_MAX_TOKENS = 8192


def _build_prompt(raw_posts: List[Dict[str, str]]) -> str:
    """Build the user prompt asking deepseek-reasoner to return a JSON array."""
    posts_json = json.dumps(raw_posts, ensure_ascii=False, indent=2)
    return (
        "You are a career-analysis assistant. Given the following intern job listings, "
        "output a JSON array of the same length. Each element must contain EXACTLY "
        "these keys (output valid JSON only, no markdown fences):\n\n"
        "  \"description\"      — 2-3 sentence summary of what the role likely involves (max 300 chars)\n"
        "  \"requirements\"     — JSON array of 2-5 likely skill keywords, e.g. [\"Python\", \"SQL\"]\n"
        "  \"companySize\"      — estimated company size, e.g. \"500-1000 employees\"\n"
        "  \"companyFounded\"   — estimated founding year, e.g. \"2015\"\n"
        "  \"companyBusiness\"  — one-line business description (max 60 chars)\n"
        "  \"fitScore\"         — star rating + comment, e.g. \"★★★★☆ Strong match for CS students\"\n"
        "  \"difficulty\"       — difficulty level, e.g. \"Medium — Competitive\"\n"
        "  \"avgSalary\"        — estimated hourly intern pay range, e.g. \"$40-55/hr\"\n\n"
        "Rules:\n"
        "- Output ONLY the JSON array, no other text.\n"
        "- Use empty string \"\" for any field you cannot determine.\n"
        "- Keep description ≤ 300 characters.\n\n"
        f"Input listings:\n{posts_json}"
    )


def _call_ai_api(raw_posts: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """Send a batch of raw posts to DeepSeek and return enrichment dicts.

    Uses OpenAI SDK with DeepSeek endpoint.
    deepseek-reasoner returns:
      choices[0].message.reasoning_content  — chain-of-thought (ignored here)
      choices[0].message.content            — final JSON answer
    """
    client = OpenAI(
        api_key=AI_API_KEY,
        base_url="https://api.deepseek.com",
    )

    response = client.chat.completions.create(
        model=AI_MODEL,
        max_tokens=_MAX_TOKENS,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a helpful career data assistant. "
                    "You must respond with valid JSON only."
                ),
            },
            {
                "role": "user",
                "content": _build_prompt(raw_posts),
            },
        ],
        # Note: temperature, top_p, presence_penalty are NOT supported
        # by deepseek-reasoner and are intentionally omitted.
    )

    # Extract JSON content from response
    content = response.choices[0].message.content.strip()
    parsed = json.loads(content)

    # The model should return a top-level array, but may wrap it in {"results": [...]}
    if isinstance(parsed, list):
        return parsed
    # Unwrap common wrapper keys
    for key in ("results", "listings", "data", "jobs", "internships"):
        if key in parsed and isinstance(parsed[key], list):
            return parsed[key]
    # Fallback: return as single-element list
    return [parsed]


def _default_enrichment() -> Dict[str, Any]:
    """Fallback enrichment when DeepSeek API key is not configured."""
    return {
        "description": "",
        "requirements": [],
        "companySize": "",
        "companyFounded": "",
        "companyBusiness": "",
        "fitScore": "",
        "difficulty": "",
        "avgSalary": "",
    }


def _api_key_is_set() -> bool:
    """Return True only if a real API key has been provided (not the placeholder)."""
    return bool(AI_API_KEY) and AI_API_KEY != "YOUR_DEEPSEEK_API_KEY_HERE"


def enrich_posts(raw_posts: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """
    Enrich a list of raw scraped posts with AI-generated data via DeepSeek.

    Parameters
    ----------
    raw_posts : list of dict
        Each dict has keys: company, title, location, applyLink

    Returns
    -------
    list of dict
        Same length, each dict includes description, requirements,
        companySize, companyFounded, companyBusiness, fitScore,
        difficulty, avgSalary.
    """
    if not _api_key_is_set():
        logger.warning(
            "DEEPSEEK_API_KEY not set (or still placeholder) — "
            "returning empty enrichment. Set your key in ai_analyzer.py or "
            "export DEEPSEEK_API_KEY=<your_key>"
        )
        return [_default_enrichment() for _ in raw_posts]

    enriched: List[Dict[str, Any]] = []
    total_batches = -(-len(raw_posts) // _BATCH_SIZE)  # ceiling division
    for i in range(0, len(raw_posts), _BATCH_SIZE):
        batch = raw_posts[i : i + _BATCH_SIZE]
        logger.info("Enriching batch %d/%d (%d posts) via DeepSeek...",
                    i // _BATCH_SIZE + 1, total_batches, len(batch))
        try:
            result = _call_ai_api(batch)
            if len(result) != len(batch):
                logger.warning(
                    "DeepSeek returned %d items for batch of %d — padding with defaults",
                    len(result), len(batch),
                )
                result.extend([_default_enrichment()] * (len(batch) - len(result)))
            enriched.extend(result)
        except Exception as e:
            logger.error("DeepSeek API error for batch %d: %s — using defaults",
                         i // _BATCH_SIZE + 1, e)
            enriched.extend([_default_enrichment()] * len(batch))

    return enriched
