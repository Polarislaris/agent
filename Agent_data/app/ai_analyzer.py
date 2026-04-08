"""
AI Analyzer — enriches raw scraped intern data with AI-generated insights.

Uses DeepSeek API (deepseek-chat) with JSON Output mode to produce:
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


# --- API keys -----
# Read at call time (not import time) so .env loaded by main.py is picked up;
# strip() removes any accidental leading/trailing spaces from the .env value.
def _get_api_key() -> str:
    return (os.getenv("DEEPSEEK_API_KEY") or "").strip()


# deepseek-chat: thinking mode of DeepSeek-V3.2, supports JSON Output
# Note: temperature / top_p / presence_penalty are NOT supported by this model
AI_MODEL: str = "deepseek-chat"

# Maximum posts to send per API call (keep batches small to stay within token limits)
_BATCH_SIZE = 5

# max_tokens for output (reasoning CoT + JSON answer); 8192 is safe for small batches
_MAX_TOKENS = 8192


def _build_prompt(raw_posts: List[Dict[str, str]]) -> str:
    """Build the user prompt asking deepseek-chat to return a JSON array."""
    posts_json = json.dumps(raw_posts, ensure_ascii=False, indent=2)
    return (
        "You are a career-analysis assistant. Given the following intern job listings "
        "(each may include a 'jobDescription' field with text scraped from the apply page), "
        "output a JSON array of the same length. Each element must contain EXACTLY "
        "these keys (output valid JSON only, no markdown fences):\n\n"
        "  \"description\"      — 2-3 sentence summary of what the role likely involves (max 300 chars). "
        "Use the jobDescription field if available for a more accurate summary.\n"
        "  \"requirements\"     — JSON array of 2-5 likely skill keywords extracted from the job description, "
        "e.g. [\"Python\", \"SQL\"]. Parse real skills from the jobDescription when present.\n"
        "  \"companySize\"      — estimated company size, e.g. \"500-1000 employees\"\n"
        "  \"companyFounded\"   — estimated founding year, e.g. \"2015\"\n"
        "  \"companyBusiness\"  — one-line business description (max 60 chars)\n"
        "  \"fitScore\"         — star rating + a 2-3 sentence analysis of how well this role fits a "
        "CS/software engineering student. Include strengths and what to prepare. "
        "e.g. \"★★★★☆ Strong match for CS students with web dev experience. "
        "The role emphasizes full-stack skills which align well with typical coursework. "
        "Brush up on system design and REST APIs.\"\n"
        "  \"difficulty\"       — difficulty level + a 2-3 sentence analysis of the application "
        "competition and interview process. e.g. \"Medium — Competitive. Expect a coding assessment "
        "followed by 1-2 technical interviews. Prepare data structures and real project examples.\"\n"
        "  \"avgSalary\"        — estimated hourly intern pay range, e.g. \"$40-55/hr\"\n\n"
        "Rules:\n"
        "- Output ONLY the JSON array, no other text.\n"
        "- Use the jobDescription field to produce more accurate and specific analysis.\n"
        "- Use empty string \"\" for any field you cannot determine.\n"
        "- Keep description ≤ 300 characters.\n"
        "- fitScore and difficulty should each be a meaningful paragraph, not just a label.\n\n"
        f"Input listings:\n{posts_json}"
    )


def _call_ai_api(raw_posts: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """Send a batch of raw posts to DeepSeek and return enrichment dicts.

    Uses OpenAI SDK with DeepSeek endpoint.
    deepseek-chat
      returns:
      choices[0].message.reasoning_content  — chain-of-thought (ignored here)
      choices[0].message.content            — final JSON answer
    """
    api_key = _get_api_key()
    masked = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "(short?)"
    logger.info("[DeepSeek] Connecting — model=%s  key=%s", AI_MODEL, masked)

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com",
    )

    prompt = _build_prompt(raw_posts)
    logger.info("[DeepSeek] Sending request — %d posts, prompt_len=%d chars",
                len(raw_posts), len(prompt))

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
                "content": prompt,
            },
        ],
        # Note: temperature, top_p, presence_penalty are NOT supported
        # by deepseek-chat and are intentionally omitted.
    )

    # Log usage and response metadata
    usage = response.usage
    if usage:
        logger.info(
            "[DeepSeek] ✅ Response received — "
            "prompt_tokens=%d  completion_tokens=%d  total_tokens=%d",
            usage.prompt_tokens, usage.completion_tokens, usage.total_tokens,
        )
    finish = response.choices[0].finish_reason
    logger.info("[DeepSeek] finish_reason=%s", finish)

    # Extract JSON content from response
    content = response.choices[0].message.content.strip()
    logger.info("[DeepSeek] Raw response preview: %s", content[:300])

    parsed = json.loads(content)

    # The model should return a top-level array, but may wrap it in {"results": [...]}
    if isinstance(parsed, list):
        logger.info("[DeepSeek] Parsed %d enrichment objects", len(parsed))
        return parsed
    # Unwrap common wrapper keys
    for key in ("results", "listings", "data", "jobs", "internships"):
        if key in parsed and isinstance(parsed[key], list):
            logger.info("[DeepSeek] Unwrapped key='%s', got %d objects", key, len(parsed[key]))
            return parsed[key]
    # Fallback: return as single-element list
    logger.warning("[DeepSeek] Unexpected response shape, keys=%s", list(parsed.keys()))
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
    key = _get_api_key()
    ok = bool(key) and key != "YOUR_DEEPSEEK_API_KEY_HERE"
    if ok:
        masked = key[:8] + "..." + key[-4:] if len(key) > 12 else key
        logger.info("[DeepSeek] API key detected: %s (len=%d)", masked, len(key))
    else:
        logger.warning("[DeepSeek] API key NOT set or still placeholder")
    return ok


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
            logger.error("[DeepSeek] ❌ API error for batch %d: %s",
                         i // _BATCH_SIZE + 1, e, exc_info=True)
            enriched.extend([_default_enrichment()] * len(batch))

    return enriched
