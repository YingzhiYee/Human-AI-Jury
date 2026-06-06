"""
Official Agent — 搜索官方声明（政府、机构、官方 X 账号）

策略：
1. 用 Brave Search 搜 site:*.gov + site:*.org 关键词
2. 用 xAPI 搜索白宫 / 司法部等官方账号推文
"""

import uuid
import json
import httpx

from ...settings import build_openai_client, get_env, get_openai_model
from ...xapi.client import XAPIClient
from ..direction_inference import refine_direction_label
from ..schema import EvidenceItem, EvidenceDirection, SourceType
from ..evidence_scoring import score_official_confidence, score_social_confidence

BRAVE_API_KEY  = get_env("BRAVE_API_KEY", "")
openai_client  = build_openai_client()
OPENAI_MODEL = get_openai_model()

# 需要检索的官方 X 账号（用于 xAPI）
OFFICIAL_ACCOUNTS = ["WhiteHouse", "POTUS", "RealDonaldTrump", "DOJ", "FBI"]


def _brave_official_search(claim: str, count: int = 5) -> list[dict]:
    query = f"{claim} site:*.gov OR site:*.org"
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": BRAVE_API_KEY,
    }
    params = {"q": query, "count": count}
    try:
        resp = httpx.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers=headers, params=params, timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("web", {}).get("results", [])
    except Exception as e:
        print(f"[OfficialAgent] Brave error: {e}")
        return []


def _xapi_official_tweets(claim: str, max_per_account: int = 2) -> list[dict]:
    """搜索官方账号与 claim 相关的推文"""
    xapi = XAPIClient()
    collected = []
    for username in OFFICIAL_ACCOUNTS:
        query = f"from:{username} {claim[:60]} -is:retweet"
        try:
            raw    = xapi.search_tweets(query=query, max_results=max_per_account)
            tweets = XAPIClient.parse_search_results(raw)
            collected.extend(tweets)
        except Exception:
            continue
    return collected


def _llm_analyze(claim: str, text: str) -> tuple[str, str, float]:
    prompt = f"""Claim: "{claim}"
Source text: "{text}"

JSON response:
{{
  "summary": "<≤80 chars>",
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
        data.get("summary", text[:80]),
        data.get("direction", "neutral"),
        float(data.get("relevance", 0.5)),
    )


def run(claim: str, max_items: int = 5) -> list[EvidenceItem]:
    items: list[EvidenceItem] = []
    direction_map = {
        "supports_yes": EvidenceDirection.SUPPORTS_YES,
        "supports_no":  EvidenceDirection.SUPPORTS_NO,
        "neutral":      EvidenceDirection.NEUTRAL,
    }

    # ── 1. 官方网站
    web_results = _brave_official_search(claim, count=max_items)
    for i, r in enumerate(web_results[:max_items]):
        url   = r.get("url", "")
        title = r.get("title", "")
        desc  = r.get("description", "")
        try:
            summary, direction_str, relevance = _llm_analyze(claim, f"{title}. {desc}")
        except Exception:
            summary, direction_str, relevance = desc[:80], "neutral", 0.5

        direction_str = refine_direction_label(
            claim,
            f"{title}. {desc}",
            direction_str,
        )

        items.append(EvidenceItem(
            id=f"official_web_{i}_{uuid.uuid4().hex[:6]}",
            source_type=SourceType.OFFICIAL,
            source_name=r.get("profile", {}).get("name", url[:40]),
            url=url,
            title=title,
            summary=summary,
            raw_snippet=desc[:300],
            direction=direction_map.get(direction_str, EvidenceDirection.NEUTRAL),
            confidence=score_official_confidence(url),
            relevance=relevance,
            agent="OfficialAgent",
        ))

    # ── 2. 官方 X 账号推文（xAPI）
    tweets = _xapi_official_tweets(claim, max_per_account=2)
    for i, t in enumerate(tweets[: max(0, max_items - len(items))]):
        try:
            summary, direction_str, relevance = _llm_analyze(claim, t["text"])
        except Exception:
            summary, direction_str, relevance = t["text"][:80], "neutral", 0.6

        direction_str = refine_direction_label(claim, t["text"], direction_str)

        confidence = score_social_confidence(
            t["author_username"], t["author_verified"],
            t["like_count"], t["retweet_count"],
        )

        items.append(EvidenceItem(
            id=f"official_x_{i}_{uuid.uuid4().hex[:6]}",
            source_type=SourceType.OFFICIAL,
            source_name=f"@{t['author_username']} (Official)",
            url=t["url"],
            title=f"Official tweet by @{t['author_username']}",
            summary=summary,
            raw_snippet=t["text"][:300],
            direction=direction_map.get(direction_str, EvidenceDirection.NEUTRAL),
            confidence=confidence,
            relevance=relevance,
            published_at=t.get("created_at", ""),
            agent="OfficialAgent",
        ))

    return items
