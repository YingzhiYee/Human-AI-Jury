"""
Social Agent — 通过 xAPI (xapi.to) 搜索 X/Twitter 相关推文

xAPI 是本项目核心 hackathon 亮点：所有 Social 层数据均走 xapi.to
"""

import json
import re
import uuid
from datetime import date, datetime, timedelta, timezone

from ...settings import build_openai_client, get_openai_model
from ...xapi.client import XAPIClient
from ..schema import EvidenceItem, EvidenceDirection, SourceType
from ..evidence_scoring import score_social_confidence

openai_client = build_openai_client()
OPENAI_MODEL = get_openai_model()

_STOPWORDS = {
    "a", "an", "and", "are", "be", "before", "by", "did", "do", "does", "for",
    "from", "get", "has", "have", "how", "if", "in", "is", "it", "its", "of",
    "on", "or", "post", "say", "that", "the", "their", "this", "to", "tweet",
    "today", "was", "week", "were", "what", "when", "where", "who", "why", "will",
    "with", "would", "yesterday", "year",
}


def _time_window_start(claim: str) -> datetime | None:
    lowered = claim.lower()
    today = date.today()
    if "today" in lowered:
        return datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)
    if "yesterday" in lowered:
        return datetime.combine(today - timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
    if "this week" in lowered or "past week" in lowered:
        start_of_week = today - timedelta(days=today.weekday())
        return datetime.combine(start_of_week, datetime.min.time(), tzinfo=timezone.utc)
    if "this month" in lowered:
        return datetime.combine(today.replace(day=1), datetime.min.time(), tzinfo=timezone.utc)
    return None


def _claim_keywords(claim: str) -> list[str]:
    cleaned = re.sub(r"[^A-Za-z0-9@# ]+", " ", claim)
    return [
        token for token in cleaned.split()
        if len(token) >= 3 and token.lower() not in _STOPWORDS
    ]


def _guess_handle(subject: str) -> str:
    handle = re.sub(r"[^A-Za-z0-9_]", "", subject.lower())
    return handle[:15]


def _extract_post_claim_parts(claim: str) -> tuple[str, str] | None:
    match = re.search(
        r"did\s+(.+?)\s+(?:post|tweet|say|write|announce)\s+about\s+(.+)",
        claim,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    return match.group(1).strip(), match.group(2).strip()


def _fallback_queries(claim: str) -> list[str]:
    keywords = _claim_keywords(claim)
    if not keywords:
        return [f"({claim[:80]}) -is:retweet lang:en".strip()]

    joined = " ".join(keywords[:6])
    queries = [f"{joined} -is:retweet lang:en".strip()]

    post_parts = _extract_post_claim_parts(claim)
    if post_parts:
        subject, topic_text = post_parts
        topic_keywords = _claim_keywords(topic_text)
        topic = " ".join(topic_keywords[:4]) or joined
        handle = _guess_handle(subject)
        if handle:
            queries.insert(0, f"from:{handle} {topic} -is:retweet".strip())
            queries.append(f"{handle} {topic} -is:retweet lang:en".strip())
        queries.append(f"{subject} {topic} -is:retweet lang:en".strip())

    if "world" in {k.lower() for k in keywords} and "cup" in {k.lower() for k in keywords}:
        sports_tokens = []
        for preferred in ("Brazil", "World", "Cup", "FIFA", "2026"):
            if preferred.lower() in {k.lower() for k in keywords}:
                sports_tokens.append(preferred)
        if sports_tokens:
            queries.insert(0, f"{' '.join(sports_tokens)} -is:retweet lang:en".strip())

    deduped: list[str] = []
    seen: set[str] = set()
    for query in queries:
        normalized = " ".join(query.split())
        if normalized and normalized not in seen:
            seen.add(normalized)
            deduped.append(normalized)
    return deduped[:4]


def _heuristic_relevance(claim: str, tweet_text: str) -> float:
    claim_tokens = {token.lower() for token in _claim_keywords(claim)}
    text_tokens = {token.lower() for token in _claim_keywords(tweet_text)}
    if not claim_tokens or not text_tokens:
        return 0.0
    focus_match = re.search(r"about\s+(.+)", claim, flags=re.IGNORECASE)
    focus_tokens = {
        token.lower()
        for token in _claim_keywords(focus_match.group(1))
    } if focus_match else claim_tokens
    focus_overlap = focus_tokens & text_tokens
    if focus_tokens and not focus_overlap:
        return 0.0
    overlap = claim_tokens & text_tokens
    focus_coverage = len(focus_overlap) / max(1, min(len(focus_tokens), 3))
    total_coverage = len(overlap) / max(1, min(len(claim_tokens), 4))
    return round(min(0.9, 0.2 + focus_coverage * 0.45 + total_coverage * 0.25), 3)


def _matches_post_subject(claim: str, tweet: dict) -> bool:
    post_parts = _extract_post_claim_parts(claim)
    if not post_parts:
        return True
    subject, _topic = post_parts
    subject_tokens = {token.lower() for token in _claim_keywords(subject)}
    text_tokens = {token.lower() for token in _claim_keywords(tweet.get("text", ""))}
    if subject_tokens & text_tokens:
        return True
    handle = _guess_handle(subject)
    return bool(handle) and tweet.get("query_used", "").startswith(f"from:{handle} ")


def _is_fresh_enough(claim: str, created_at: str) -> bool:
    window_start = _time_window_start(claim)
    if window_start is None or not created_at:
        return True
    try:
        published = datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y")
    except ValueError:
        return True
    return published >= window_start


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
        model=OPENAI_MODEL,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=120,
    )
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
    queries = _fallback_queries(claim)
    tweets: list[dict] = []
    seen_tweet_ids: set[str] = set()

    for query in queries:
        try:
            raw = xapi.search_tweets(query=query, max_results=max_items * 2)
        except Exception as e:
            print(f"[SocialAgent] xAPI error for query '{query}': {e}")
            continue

        for tweet in XAPIClient.parse_search_results(raw):
            tweet_id = tweet.get("id")
            if tweet_id and tweet_id not in seen_tweet_ids:
                if not _is_fresh_enough(claim, tweet.get("created_at", "")):
                    continue
                seen_tweet_ids.add(tweet_id)
                tweet["query_used"] = query
                tweets.append(tweet)
        if len(tweets) >= max_items * 2:
            break

    if not tweets:
        return []

    items: list[EvidenceItem] = []

    for t in tweets:
        try:
            summary, direction_str, relevance = _llm_analyze(claim, t["text"])
        except Exception as exc:
            print(f"[SocialAgent] LLM analyze fallback: {exc}")
            summary = t["text"][:80]
            direction_str = "neutral"
            relevance = _heuristic_relevance(claim, t["text"])

        if relevance < 0.25:
            continue
        if not _matches_post_subject(claim, t):
            continue

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

        source_name = t["author_username"]
        if source_name and not source_name.startswith("@") and not source_name.startswith("user:"):
            source_name = f"@{source_name}"
        items.append(
            EvidenceItem(
                id=f"social_{len(items)}_{uuid.uuid4().hex[:6]}",
                source_type=SourceType.SOCIAL,
                source_name=source_name or "user:unknown",
                url=t["url"],
                title=f"Tweet by {source_name or 'user:unknown'}",
                summary=summary,
                raw_snippet=t["text"][:300],
                direction=direction_map.get(direction_str, EvidenceDirection.NEUTRAL),
                confidence=confidence,
                relevance=relevance,
                published_at=t.get("created_at", ""),
                agent="SocialAgent",
            )
        )
        if len(items) >= max_items:
            break

    return items
