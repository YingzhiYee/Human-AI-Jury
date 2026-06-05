"""
Evidence Scoring — 来源可信度 & 相关度打分

confidence 规则：
  官方政府 / 机构账号        0.95
  主流权威媒体（Reuters等）  0.90
  知名媒体                   0.80
  认证 X 账号（高互动）      0.70
  认证 X 账号（低互动）      0.60
  未认证 X 账号（高互动）    0.55
  未认证 X 账号              0.40
  未知来源                   0.30

relevance 由 LLM 0-1 打分后传入，此模块只做 weight = confidence × relevance
"""

import re
from .schema import EvidenceItem, SourceType

# 权威新闻来源域名 → confidence
NEWS_SOURCE_CONFIDENCE: dict[str, float] = {
    "reuters.com":       0.92,
    "apnews.com":        0.91,
    "bbc.com":           0.88,
    "bbc.co.uk":         0.88,
    "nytimes.com":       0.85,
    "washingtonpost.com":0.85,
    "theguardian.com":   0.83,
    "politico.com":      0.82,
    "axios.com":         0.80,
    "npr.org":           0.80,
    "thehill.com":       0.75,
    "foxnews.com":       0.72,
    "cnn.com":           0.75,
    "nbcnews.com":       0.75,
    "cbsnews.com":       0.75,
}

# 官方 X 账号 → confidence
OFFICIAL_ACCOUNTS: dict[str, float] = {
    "whitehouse":      0.97,
    "potus":           0.97,
    "realdonaldtrump": 0.95,
    "joebiden":        0.95,
    "doj":             0.95,
    "fbi":             0.95,
    "usdoj":           0.95,
    "speakerjohnson":  0.88,
    "senatemajldr":    0.88,
}


def score_news_confidence(url: str) -> float:
    """根据新闻 URL 的域名判断可信度"""
    domain = _extract_domain(url)
    for key, score in NEWS_SOURCE_CONFIDENCE.items():
        if key in domain:
            return score
    return 0.50   # 默认未知媒体


def score_social_confidence(
    author_username: str,
    author_verified: bool,
    like_count: int,
    retweet_count: int,
) -> float:
    """根据 X 账号特征打分"""
    username_lower = author_username.lower()

    # 官方账号最高优先
    if username_lower in OFFICIAL_ACCOUNTS:
        return OFFICIAL_ACCOUNTS[username_lower]

    engagement = like_count + retweet_count * 2

    if author_verified:
        if engagement >= 1000:
            return 0.72
        elif engagement >= 100:
            return 0.65
        else:
            return 0.58
    else:
        if engagement >= 5000:
            return 0.55
        elif engagement >= 500:
            return 0.45
        else:
            return 0.38


def score_official_confidence(url: str) -> float:
    """政府 / 机构域名打分"""
    domain = _extract_domain(url)
    if domain.endswith(".gov") or domain.endswith(".gov.cn"):
        return 0.96
    if domain.endswith(".mil"):
        return 0.95
    if domain.endswith(".edu"):
        return 0.80
    if domain.endswith(".org"):
        return 0.70
    return score_news_confidence(url)   # fallback 到新闻规则


def compute_weight(item: EvidenceItem) -> float:
    """weight = confidence × relevance，写回 item.weight"""
    item.weight = round(item.confidence * item.relevance, 4)
    return item.weight


def finalize_items(items: list[EvidenceItem]) -> list[EvidenceItem]:
    """批量计算 weight，按 weight 降序排列"""
    for item in items:
        compute_weight(item)
    return sorted(items, key=lambda x: x.weight, reverse=True)


# ──────────────────────────────────────────
# 内部工具
# ──────────────────────────────────────────

def _extract_domain(url: str) -> str:
    match = re.search(r"https?://([^/]+)", url)
    return match.group(1).lower() if match else url.lower()
