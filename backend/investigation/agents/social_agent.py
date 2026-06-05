"""
Social Agent — 通过 xAPI (xapi.to) 搜索 X/Twitter 相关推文

xAPI 是本项目核心 hackathon 亮点：所有 Social 层数据均走 xapi.to
"""

import os
import uuid
from openai import OpenAI

from ...xapi.client import XAPIClient
from ..schema import EvidenceItem, EvidenceDirection, SourceType
from ..evidence_scoring import score_social_confidence

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "sk-placeholder"))


def _build_query(claim: str) -> str:
    """构造 xAPI 搜索语句，过滤转发和低质量内容"""
    keywords = claim[:80]   # 截断避免超长
    return f"({keywords}) -is:retweet lang:en"


def _llm_analyze(claim: str, tweet_text: str) -> tuple[str, str, float]:
    """
    用 LLM 提炼摘要、判断立场、评估相关度
    返回 (summary, direction_str, relevance)
    """
    prompt = f"""You are a fact-checking assistant.

Claim: "{claim}"
Tweet: "{tweet_text}"

Respond in JSON with exactly these fields:
{{
  "summary": "<one sentence summary in English, ≤80 chars>",
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
    import json
    data = json.loads(resp.choices[0].message.content)
    return (
        data.get("summary", tweet_text[:80]),
        data.get("direction", "neutral"),
        float(data.get("relevance", 0.5)),
    )


def run(claim: str, max_items: int = 5) -> list[EvidenceItem]:
    """
    Social Agent 主入口
    返回 EvidenceItem 列表，confidence 已计算，relevance/weight 由 pipeline 统一处理
    """
    xapi = XAPIClient()
    query = _build_query(claim)

    try:
        raw = xapi.search_tweets(query=query, max_results=max_items * 2)
    except Exception as e:
        print(f"[SocialAgent] xAPI error: {e}")
        return []

    tweets = XAPIClient.parse_search_results(raw)
    items: list[EvidenceItem] = []

    for i, t in enumerate(tweets[:max_items]):
        try:
            summary, direction_str, relevance = _llm_analyze(claim, t["text"])
        except Exception:
            summary    = t["text"][:80]
            direction_str = "neutral"
            relevance  = 0.4

        confidence = score_social_confidence(
            author_username=t["author_username"],
            author_verified=t["author_verified"],
            like_count=t["like_count"],
            retweet_count=t["retweet_count"],
        )

        direction_map = {
            "supports_yes": EvidenceDirection.SUPPORTS_YES,
            "supports_no":  EvidenceDirection.SUPPORTS_NO,
            "neutral":      EvidenceDirection.NEUTRAL,
        }

        items.append(EvidenceItem(
            id=f"social_{i}_{uuid.uuid4().hex[:6]}",
            source_type=SourceType.SOCIAL,
            source_name=f"@{t['author_username']}",
            url=t["url"],
            title=f"Tweet by @{t['author_username']}",
            summary=summary,
            raw_snippet=t["text"][:300],
            direction=direction_map.get(direction_str, EvidenceDirection.NEUTRAL),
            confidence=confidence,
            relevance=relevance,
            published_at=t.get("created_at", ""),
            agent="SocialAgent",
        ))

    return items
