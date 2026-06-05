"""
Mock Data — Hackathon Demo Fallback

当 API 限速 / 网络异常时使用预缓存数据，确保 Demo 流畅。
用法：在 pipeline.py 中 import 并调用 get_mock_pool()
"""

from .schema import EvidencePool, EvidenceItem, EvidenceDirection, SourceType

DEMO_CLAIM = "Trump will pardon Hunter Biden before Jan 20, 2025 inauguration"
DEMO_MARKET_ID = "pm_demo_001"


def get_mock_pool() -> EvidencePool:
    items = [
        EvidenceItem(
            id="news_0_mock",
            source_type=SourceType.NEWS,
            source_name="Reuters",
            url="https://www.reuters.com/world/us/trump-pardon-hunter-biden-2025-01-15/",
            title="Trump signals possible pardon for Hunter Biden before inauguration",
            summary="Reuters reports Trump advisors discussed pardon options for Hunter Biden.",
            raw_snippet="Multiple sources familiar with the matter told Reuters that Trump transition team...",
            direction=EvidenceDirection.SUPPORTS_YES,
            confidence=0.92,
            relevance=0.91,
            weight=0.8372,
            published_at="2025-01-15T10:00:00Z",
            agent="NewsAgent",
        ),
        EvidenceItem(
            id="social_0_mock",
            source_type=SourceType.SOCIAL,
            source_name="@RealDonaldTrump",
            url="https://x.com/realdonaldtrump/status/1749000000000000001",
            title="Tweet by @RealDonaldTrump",
            summary="Trump posted ambiguous statement about 'healing the nation' on X.",
            raw_snippet="America needs to heal. We must move forward together as one nation. MAGA!",
            direction=EvidenceDirection.NEUTRAL,
            confidence=0.95,
            relevance=0.55,
            weight=0.5225,
            published_at="2025-01-14T18:30:00Z",
            agent="SocialAgent",
        ),
        EvidenceItem(
            id="official_0_mock",
            source_type=SourceType.OFFICIAL,
            source_name="@WhiteHouse",
            url="https://x.com/whitehouse/status/1749000000000000002",
            title="Official tweet by @WhiteHouse",
            summary="Biden White House stated no preemptive pardon had been issued.",
            raw_snippet="The White House has no plans to issue a preemptive pardon for Hunter Biden.",
            direction=EvidenceDirection.SUPPORTS_NO,
            confidence=0.97,
            relevance=0.95,
            weight=0.9215,
            published_at="2025-01-10T14:00:00Z",
            agent="OfficialAgent",
        ),
        EvidenceItem(
            id="counter_0_mock",
            source_type=SourceType.COUNTER,
            source_name="Politico",
            url="https://www.politico.com/news/2025/01/trump-pardon-hunter-unlikely",
            title="Legal experts say Trump pardon of Hunter Biden highly unlikely",
            summary="Constitutional scholars argue Trump lacks authority to pardon before taking office.",
            raw_snippet="Several constitutional law experts told Politico that a president-elect cannot issue pardons...",
            direction=EvidenceDirection.SUPPORTS_NO,
            confidence=0.82,
            relevance=0.88,
            weight=0.7216,
            published_at="2025-01-12T09:00:00Z",
            agent="CounterAgent",
        ),
        EvidenceItem(
            id="news_1_mock",
            source_type=SourceType.NEWS,
            source_name="AP News",
            url="https://apnews.com/article/hunter-biden-pardon-trump-2025",
            title="Hunter Biden pardon uncertainty grows as inauguration nears",
            summary="AP reports growing uncertainty over Hunter Biden pardon status.",
            raw_snippet="As inauguration day approaches, questions about Hunter Biden's legal fate remain unresolved...",
            direction=EvidenceDirection.NEUTRAL,
            confidence=0.91,
            relevance=0.78,
            weight=0.7098,
            published_at="2025-01-16T08:00:00Z",
            agent="NewsAgent",
        ),
    ]

    pool = EvidencePool(
        market_id=DEMO_MARKET_ID,
        claim=DEMO_CLAIM,
        items=items,
    )
    pool.compute_summary()
    return pool
