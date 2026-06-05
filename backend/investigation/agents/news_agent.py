"""
News Agent — 通过 Brave Search API 搜索新闻报道
"""

import os
import uuid
import json
import httpx
from openai import OpenAI

from ..schema import EvidenceItem, EvidenceDirection, SourceType
from ..evidence_scoring import score_news_confidence

BRAVE_API_KEY  = os.getenv("BRAVE_API_KEY", "")
BRAVE_BASE_URL = "https://api.search.brave.com/res/v1/news/search"

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "sk-placeholder"))


def _brave_news_search(query: str, count: int = 10) -> list[dict]:
    """调用 Brave Search News API"""
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": BRAVE_API_KEY,
    }
    params = {"q": query, "count": count, "freshness": "pw"}   # pw = past week
    try:
        resp = httpx.get(BRAVE_BASE_URL, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        results = resp.json().get("results", [])
        return results
    except Exception as e:
        print(f"[NewsAgent] Brave Search error: {e}")
        return []


def _llm_analyze(claim: str, title: str, description: str) -> tuple[str, str, float]:
    prompt = f"""You are a fact-checking assistant.

Claim: "{claim}"
Article title: "{title}"
Article snippet: "{description}"

Respond in JSON:
{{
  "summary": "<one sentence, ≤80 chars>",
  "direction": "supports_yes" | "supports_no" | "neutral",
  "relevance": <float 0.0-1.0>
}}"""

    resp = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=120,
    )
    data = json.loads(resp.choices[0].message.content)
    return (
        data.get("summary", title[:80]),
        data.get("direction", "neutral"),
        float(data.get("relevance", 0.5)),
    )


def run(claim: str, max_items: int = 5) -> list[EvidenceItem]:
    """News Agent 主入口"""
    results = _brave_news_search(claim, count=max_items * 2)
    items: list[EvidenceItem] = []

    direction_map = {
        "supports_yes": EvidenceDirection.SUPPORTS_YES,
        "supports_no":  EvidenceDirection.SUPPORTS_NO,
        "neutral":      EvidenceDirection.NEUTRAL,
    }

    for i, r in enumerate(results[:max_items]):
        title       = r.get("title", "")
        url         = r.get("url", "")
        description = r.get("description", "")
        published   = r.get("age", "")

        try:
            summary, direction_str, relevance = _llm_analyze(claim, title, description)
        except Exception:
            summary       = description[:80] or title[:80]
            direction_str = "neutral"
            relevance     = 0.5

        confidence = score_news_confidence(url)

        items.append(EvidenceItem(
            id=f"news_{i}_{uuid.uuid4().hex[:6]}",
            source_type=SourceType.NEWS,
            source_name=r.get("source", {}).get("name", url),
            url=url,
            title=title,
            summary=summary,
            raw_snippet=description[:300],
            direction=direction_map.get(direction_str, EvidenceDirection.NEUTRAL),
            confidence=confidence,
            relevance=relevance,
            published_at=published,
            agent="NewsAgent",
        ))

    return items
