"""
Counter-Evidence Agent — 主动搜索与主流观点相反的证据

策略：对 claim 取反后搜索，确保证据池的多元性，避免确认偏差
"""

import uuid
import json
import httpx

from ...settings import build_openai_client, get_env, get_openai_model
from ..schema import EvidenceItem, EvidenceDirection, SourceType
from ..evidence_scoring import score_news_confidence

BRAVE_API_KEY = get_env("BRAVE_API_KEY", "")
openai_client = build_openai_client()
OPENAI_MODEL = get_openai_model()


def _generate_counter_query(claim: str) -> str:
    """用 LLM 生成反向搜索关键词"""
    prompt = f"""Given this claim: "{claim}"
Generate a search query (≤12 words) to find evidence that CONTRADICTS or DISPUTES this claim.
Respond with ONLY the search query, no explanation."""

    resp = openai_client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=30,
    )
    return resp.choices[0].message.content.strip().strip('"')


def _brave_search(query: str, count: int = 8) -> list[dict]:
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": BRAVE_API_KEY,
    }
    params = {"q": query, "count": count, "freshness": "pm"}   # pm = past month
    try:
        resp = httpx.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers=headers, params=params, timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("web", {}).get("results", [])
    except Exception as e:
        print(f"[CounterAgent] Brave error: {e}")
        return []


def _llm_analyze(claim: str, title: str, snippet: str) -> tuple[str, str, float]:
    prompt = f"""Claim: "{claim}"
Article: "{title}. {snippet}"

Classify the article RELATIVE TO THE ORIGINAL CLAIM.
- Use "supports_yes" if it supports the claim being true.
- Use "supports_no" if it contradicts the claim or supports the opposite outcome.
- Use "neutral" if the article is mixed, speculative, or unclear.

JSON:
{{
  "summary": "<=80 chars summarizing how this evidence relates to the claim>",
  "direction": "supports_yes" | "supports_no" | "neutral",
  "relevance": <0.0-1.0>
}}"""
    resp = openai_client.chat.completions.create(
        model=OPENAI_MODEL,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=120,
    )
    data = json.loads(resp.choices[0].message.content)
    return (
        data.get("summary", snippet[:80]),
        data.get("direction", "supports_no"),
        float(data.get("relevance", 0.5)),
    )


def run(claim: str, max_items: int = 5) -> list[EvidenceItem]:
    """Counter-Evidence Agent 主入口"""
    try:
        counter_query = _generate_counter_query(claim)
    except Exception:
        counter_query = f"NOT {claim[:60]}"

    print(f"[CounterAgent] Counter query: {counter_query}")
    results = _brave_search(counter_query, count=max_items * 2)
    items: list[EvidenceItem] = []

    direction_map = {
        "supports_yes": EvidenceDirection.SUPPORTS_YES,
        "supports_no":  EvidenceDirection.SUPPORTS_NO,
        "neutral":      EvidenceDirection.NEUTRAL,
    }

    for i, r in enumerate(results[:max_items]):
        url     = r.get("url", "")
        title   = r.get("title", "")
        snippet = r.get("description", "")

        try:
            summary, direction_str, relevance = _llm_analyze(claim, title, snippet)
        except Exception:
            summary, direction_str, relevance = snippet[:80], "neutral", 0.5

        items.append(EvidenceItem(
            id=f"counter_{i}_{uuid.uuid4().hex[:6]}",
            source_type=SourceType.COUNTER,
            source_name=r.get("profile", {}).get("name", url[:40]),
            url=url,
            title=title,
            summary=summary,
            raw_snippet=snippet[:300],
            direction=direction_map.get(direction_str, EvidenceDirection.NEUTRAL),
            confidence=score_news_confidence(url),
            relevance=relevance,
            agent="CounterAgent",
        ))

    return items
