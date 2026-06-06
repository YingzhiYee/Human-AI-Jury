"""
Investigation Layer 功能验证脚本

不需要真实 API Key，用 mock 验证：
1. schema 数据结构正确
2. evidence_scoring 打分逻辑正确
3. xAPI client 能构造出合法请求
4. 各 Agent 在 mock 下能返回 EvidenceItem
5. pipeline 能跑通并输出 EvidencePool
6. mock_data fallback 可用
"""

import sys
import os
import json
from unittest.mock import patch, MagicMock

# 必须在 import 任何 backend 模块之前设好假 Key
# OpenAI SDK 初始化时只做格式校验，不发请求
os.environ.setdefault("OPENAI_API_KEY", "sk-test-placeholder-for-unit-tests")
os.environ.setdefault("XAPI_TOKEN",     "xapi-test-placeholder")
os.environ.setdefault("BRAVE_API_KEY",  "brave-test-placeholder")

sys.path.insert(0, os.path.dirname(__file__))

PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"

def check(name: str, fn):
    try:
        fn()
        print(f"  {PASS} {name}")
        return True
    except Exception as e:
        print(f"  {FAIL} {name}")
        print(f"      └─ {e}")
        return False


# ─────────────────────────────────────────────
# 1. Schema
# ─────────────────────────────────────────────
print("\n【1】Schema 数据结构")

def test_schema_evidence_item():
    from backend.investigation.schema import EvidenceItem, EvidenceDirection, SourceType
    item = EvidenceItem(
        id="news_0_test",
        source_type=SourceType.NEWS,
        source_name="Reuters",
        url="https://reuters.com/article/123",
        title="Test Article",
        summary="This is a test summary.",
        raw_snippet="Full text snippet here.",
        direction=EvidenceDirection.SUPPORTS_YES,
        confidence=0.92,
        relevance=0.88,
    )
    assert item.confidence == 0.92
    assert item.direction == EvidenceDirection.SUPPORTS_YES

def test_schema_evidence_pool():
    from backend.investigation.schema import EvidencePool, EvidenceItem, EvidenceDirection, SourceType
    item1 = EvidenceItem(
        id="a", source_type=SourceType.NEWS, source_name="Reuters",
        url="https://r.com", title="T", summary="S", raw_snippet="R",
        direction=EvidenceDirection.SUPPORTS_YES,
        confidence=0.9, relevance=0.8, weight=0.72,
    )
    item2 = EvidenceItem(
        id="b", source_type=SourceType.SOCIAL, source_name="@abc",
        url="https://x.com/abc/1", title="T2", summary="S2", raw_snippet="R2",
        direction=EvidenceDirection.SUPPORTS_NO,
        confidence=0.7, relevance=0.6, weight=0.42,
    )
    pool = EvidencePool(market_id="pm_001", claim="test claim", items=[item1, item2])
    pool.compute_summary()
    assert pool.yes_weight == 0.72
    assert pool.no_weight  == 0.42
    assert pool.total_items == 2

def test_schema_request():
    from backend.investigation.schema import InvestigationRequest
    req = InvestigationRequest(market_id="pm_001", claim="Trump pardon Hunter Biden")
    assert req.max_items_per_agent == 5  # 默认值

check("EvidenceItem 结构正确", test_schema_evidence_item)
check("EvidencePool compute_summary 正确", test_schema_evidence_pool)
check("InvestigationRequest 默认值正确", test_schema_request)


# ─────────────────────────────────────────────
# 2. Evidence Scoring
# ─────────────────────────────────────────────
print("\n【2】Evidence Scoring 打分逻辑")

def test_news_confidence():
    from backend.investigation.evidence_scoring import score_news_confidence
    assert score_news_confidence("https://reuters.com/article") == 0.92
    assert score_news_confidence("https://bbc.com/news/1") == 0.88
    assert score_news_confidence("https://unknownblog.io/post") == 0.50

def test_social_confidence():
    from backend.investigation.evidence_scoring import score_social_confidence
    # 官方账号最高分
    score = score_social_confidence("whitehouse", True, 50000, 10000)
    assert score == 0.97
    # 高互动认证账号
    score = score_social_confidence("someuser", True, 2000, 500)
    assert score == 0.72
    # 未认证低互动
    score = score_social_confidence("randomperson", False, 10, 2)
    assert score == 0.38

def test_official_confidence():
    from backend.investigation.evidence_scoring import score_official_confidence
    assert score_official_confidence("https://whitehouse.gov/press") == 0.96
    assert score_official_confidence("https://doj.mil/statement") == 0.95

def test_compute_weight():
    from backend.investigation.schema import EvidenceItem, EvidenceDirection, SourceType
    from backend.investigation.evidence_scoring import compute_weight
    item = EvidenceItem(
        id="x", source_type=SourceType.NEWS, source_name="AP",
        url="https://ap.com", title="T", summary="S", raw_snippet="R",
        direction=EvidenceDirection.NEUTRAL,
        confidence=0.9, relevance=0.8,
    )
    w = compute_weight(item)
    assert abs(w - 0.72) < 0.001
    assert item.weight == w

check("news confidence 打分正确", test_news_confidence)
check("social confidence 打分正确（含官方账号）", test_social_confidence)
check("official confidence 打分正确（.gov/.mil）", test_official_confidence)
check("weight = confidence × relevance", test_compute_weight)


# ─────────────────────────────────────────────
# 3. xAPI Client
# ─────────────────────────────────────────────
print("\n【3】xAPI Client")

def test_xapi_client_init():
    from backend.xapi.client import XAPIClient
    client = XAPIClient(token="test_token_123")
    assert "Bearer test_token_123" in client.headers["Authorization"]

def test_xapi_parse_search_results():
    from backend.xapi.client import XAPIClient
    mock_raw = {
        "data": [
            {"id": "1234", "text": "Trump pardon news", "author_id": "u1",
             "created_at": "2025-01-15T10:00:00Z",
             "public_metrics": {"like_count": 500, "retweet_count": 100}},
        ],
        "includes": {
            "users": [{"id": "u1", "username": "newsaccount", "verified": True}]
        }
    }
    results = XAPIClient.parse_search_results(mock_raw)
    assert len(results) == 1
    assert results[0]["author_username"] == "newsaccount"
    assert results[0]["author_verified"] == True
    assert results[0]["like_count"] == 500
    assert "x.com" in results[0]["url"]

def test_xapi_request_structure():
    """验证 xAPI 请求头结构正确（mock httpx，不发真实请求）"""
    from backend.xapi.client import XAPIClient
    import httpx

    mock_response = MagicMock()
    mock_response.json.return_value = {"data": [], "includes": {"users": []}}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.Client") as mock_client_class:
        mock_ctx = MagicMock()
        mock_ctx.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_ctx

        client = XAPIClient(token="xapi_test_token")
        result = client.search_tweets("Trump pardon Hunter Biden", max_results=5)

        # 验证调用了正确的 endpoint
        call_args = mock_ctx.get.call_args
        assert "tweets/search/recent" in call_args[0][0]
        assert call_args[1]["params"]["max_results"] == 5

check("XAPIClient 初始化 Bearer token 正确", test_xapi_client_init)
check("parse_search_results 解析推文结构正确", test_xapi_parse_search_results)
check("xAPI search 请求 endpoint 和参数正确", test_xapi_request_structure)


# ─────────────────────────────────────────────
# 4. 各 Agent（mock 外部调用）
# ─────────────────────────────────────────────
print("\n【4】Agent 单元验证（mock 外部 API）")

MOCK_LLM_RESPONSE = json.dumps({
    "summary": "Test summary under 80 chars",
    "direction": "supports_yes",
    "relevance": 0.85,
})

def make_mock_openai():
    mock_choice = MagicMock()
    mock_choice.message.content = MOCK_LLM_RESPONSE
    mock_resp = MagicMock()
    mock_resp.choices = [mock_choice]
    mock_openai = MagicMock()
    mock_openai.chat.completions.create.return_value = mock_resp
    return mock_openai

def test_social_agent():
    from backend.investigation.agents import social_agent

    mock_xapi_raw = {
        "data": [
            {"id": f"t{i}", "text": f"Tweet about pardon #{i}", "author_id": f"u{i}",
             "created_at": "2025-01-15T10:00:00Z",
             "public_metrics": {"like_count": 1000, "retweet_count": 200}}
            for i in range(3)
        ],
        "includes": {"users": [
            {"id": f"u{i}", "username": f"user{i}", "verified": True}
            for i in range(3)
        ]}
    }

    with patch.object(social_agent, "openai_client", make_mock_openai()), \
         patch("backend.xapi.client.XAPIClient.search_tweets", return_value=mock_xapi_raw):
        items = social_agent.run("Trump pardon Hunter Biden", max_items=3)

    assert len(items) == 3
    assert all(i.source_type.value == "social" for i in items)
    assert all(i.agent == "SocialAgent" for i in items)
    assert all(0 <= i.confidence <= 1 for i in items)

def test_news_agent():
    from backend.investigation.agents import news_agent

    mock_brave_results = [
        {"title": f"News {i}", "url": f"https://reuters.com/article/{i}",
         "description": f"Description {i}", "age": "2025-01-15",
         "source": {"name": "Reuters"}}
        for i in range(4)
    ]

    with patch.object(news_agent, "openai_client", make_mock_openai()), \
         patch("backend.investigation.agents.news_agent._brave_news_search",
               return_value=mock_brave_results):
        items = news_agent.run("Trump pardon Hunter Biden", max_items=3)

    assert len(items) == 3
    assert all(i.source_type.value == "news" for i in items)
    assert items[0].confidence == 0.92   # reuters 应得 0.92

def test_counter_agent():
    from backend.investigation.agents import counter_agent
    from backend.investigation.schema import EvidenceDirection

    mock_brave_results = [
        {"title": f"Counter {i}", "url": f"https://politico.com/article/{i}",
         "description": f"Disputes the claim {i}"}
        for i in range(3)
    ]

    with patch.object(counter_agent, "openai_client", make_mock_openai()), \
         patch("backend.investigation.agents.counter_agent._generate_counter_query",
               return_value="Trump NOT pardon Hunter Biden unlikely"), \
         patch("backend.investigation.agents.counter_agent._brave_search",
               return_value=mock_brave_results):
        items = counter_agent.run("Trump pardon Hunter Biden", max_items=3)

    assert len(items) == 3
    assert all(i.source_type.value == "counter" for i in items)
    assert all(i.agent == "CounterAgent" for i in items)
    assert all(i.direction == EvidenceDirection.SUPPORTS_YES for i in items)

def test_counter_agent_llm_failure_falls_back_to_neutral():
    from backend.investigation.agents import counter_agent
    from backend.investigation.schema import EvidenceDirection

    mock_brave_results = [
        {
            "title": "Counter fallback",
            "url": "https://example.com/counter",
            "description": "Mixed or unclear signal",
        }
    ]

    with patch("backend.investigation.agents.counter_agent._generate_counter_query",
               return_value="counter example"), \
         patch("backend.investigation.agents.counter_agent._brave_search",
               return_value=mock_brave_results), \
         patch("backend.investigation.agents.counter_agent._llm_analyze",
               side_effect=RuntimeError("llm unavailable")):
        items = counter_agent.run("Test claim", max_items=1)

    assert len(items) == 1
    assert items[0].direction == EvidenceDirection.NEUTRAL

check("SocialAgent 返回正确 EvidenceItem（mock xAPI）", test_social_agent)
check("NewsAgent 返回正确 EvidenceItem（mock Brave）", test_news_agent)
check("CounterAgent 返回正确 EvidenceItem（mock Brave）", test_counter_agent)
check("CounterAgent 在 LLM 失败时回退到 neutral", test_counter_agent_llm_failure_falls_back_to_neutral)


# ─────────────────────────────────────────────
# 5. Pipeline 端到端（mock 所有 Agent）
# ─────────────────────────────────────────────
print("\n【5】Pipeline 端到端（mock 四个 Agent）")

def test_pipeline_end_to_end():
    from backend.investigation.schema import EvidenceItem, EvidenceDirection, SourceType

    def make_item(idx: str, direction: EvidenceDirection) -> EvidenceItem:
        return EvidenceItem(
            id=f"test_{idx}", source_type=SourceType.NEWS, source_name="TestSrc",
            url="https://example.com", title="T", summary="S", raw_snippet="R",
            direction=direction, confidence=0.8, relevance=0.9,
        )

    mock_social   = [make_item("s1", EvidenceDirection.SUPPORTS_YES),
                     make_item("s2", EvidenceDirection.NEUTRAL)]
    mock_news     = [make_item("n1", EvidenceDirection.SUPPORTS_YES)]
    mock_official = [make_item("o1", EvidenceDirection.SUPPORTS_NO)]
    mock_counter  = [make_item("c1", EvidenceDirection.SUPPORTS_NO)]

    with patch("backend.investigation.pipeline.social_agent.run",   return_value=mock_social), \
         patch("backend.investigation.pipeline.news_agent.run",     return_value=mock_news), \
         patch("backend.investigation.pipeline.official_agent.run", return_value=mock_official), \
         patch("backend.investigation.pipeline.counter_agent.run",  return_value=mock_counter):

        from backend.investigation.schema import InvestigationRequest
        from backend.investigation.pipeline import run_investigation

        req  = InvestigationRequest(market_id="pm_test", claim="Test claim")
        pool = run_investigation(req)

    assert pool.market_id == "pm_test"
    assert pool.total_items == 5                  # 2+1+1+1
    assert pool.yes_weight > 0
    assert pool.no_weight  > 0
    # items 按 weight 降序排列
    weights = [i.weight for i in pool.items]
    assert weights == sorted(weights, reverse=True)
    # 每条 item 都有 weight 已计算
    assert all(i.weight > 0 for i in pool.items)

check("Pipeline 并行运行四 Agent，汇聚成 EvidencePool", test_pipeline_end_to_end)


# ─────────────────────────────────────────────
# 6. Mock Data Fallback
# ─────────────────────────────────────────────
print("\n【6】Mock Data Fallback")

def test_mock_data():
    from backend.investigation.mock_data import get_mock_pool
    pool = get_mock_pool()
    assert pool.total_items == 5
    assert pool.yes_weight > 0
    assert pool.no_weight  > 0
    directions = {i.direction.value for i in pool.items}
    assert "supports_yes" in directions
    assert "supports_no"  in directions
    # 验证每条有完整字段
    for item in pool.items:
        assert item.url.startswith("http")
        assert 0 < item.confidence <= 1
        assert 0 < item.relevance  <= 1
        assert item.weight > 0

check("get_mock_pool() 数据完整，yes/no 双方向均有证据", test_mock_data)


# ─────────────────────────────────────────────
# 7. Deliberation 结果合理性
# ─────────────────────────────────────────────
print("\n【7】Deliberation 结果合理性")

def test_judge_confidence_varies_with_signal_strength():
    from backend.agents.judge_agent import JudgeAgent
    from backend.models import AggregationReport, BayesianSnapshot, Stance

    judge = JudgeAgent()

    mixed_snapshot = BayesianSnapshot(
        prior_yes=0.5,
        posterior_yes=0.48,
        evidence_yes_strength=0.8,
        evidence_no_strength=0.7,
        human_yes_strength=0.0,
        human_no_strength=0.0,
        challenge_pressure=0.0,
        disagreement=0.85,
        confidence_interval=0.22,
    )
    mixed_report = AggregationReport(
        prosecutor_score=0.49,
        defense_score=0.51,
        leading_stance=Stance.NEUTRAL,
        conflict_level=0.9,
        decisive_evidence_ids=[],
        notes=[],
    )

    decisive_snapshot = BayesianSnapshot(
        prior_yes=0.5,
        posterior_yes=0.08,
        evidence_yes_strength=0.2,
        evidence_no_strength=2.1,
        human_yes_strength=0.0,
        human_no_strength=0.0,
        challenge_pressure=0.0,
        disagreement=0.05,
        confidence_interval=0.12,
    )
    decisive_report = AggregationReport(
        prosecutor_score=0.18,
        defense_score=0.92,
        leading_stance=Stance.NO,
        conflict_level=0.05,
        decisive_evidence_ids=["a", "b"],
        notes=[],
    )

    mixed_confidence = judge._compute_final_confidence(mixed_snapshot, mixed_report)
    decisive_confidence = judge._compute_final_confidence(
        decisive_snapshot,
        decisive_report,
    )

    assert decisive_confidence > mixed_confidence
    assert mixed_confidence < 0.6
    assert decisive_confidence > 0.7

check("JudgeAgent 的 final confidence 会随证据强弱变化", test_judge_confidence_varies_with_signal_strength)


# ─────────────────────────────────────────────
# 汇总
# ─────────────────────────────────────────────
print()
print("=" * 40)
print("验证完成。如有 ✗ 请检查对应模块。")
print("真实 API 功能需配置 .env 后手动测试。")
