# Investigation Layer — 接口规范文档

> 队友A 负责实现，本文档说明与上下游的数据契约。

---

## 1. 整体数据流

```
Frontend / Deliberation Engine
        │  POST /api/investigation/run
        │  { market_id, claim, context, max_items_per_agent }
        ▼
  Investigation Layer
  ┌─────────────────────────────────────────┐
  │  SocialAgent   ← xAPI (xapi.to)        │
  │  NewsAgent     ← Brave Search          │  → EvidencePool (JSON)
  │  OfficialAgent ← xAPI + Brave          │
  │  CounterAgent  ← Brave + LLM反向查询   │
  └─────────────────────────────────────────┘
        │
        ▼
  Deliberation Engine（Owner负责）
  消费 EvidencePool → Prosecutor / Defense / Judge Agent
```

---

## 2. 请求格式（上游 → 调查层）

```json
POST /api/investigation/run
Content-Type: application/json

{
  "market_id": "pm_001",
  "claim": "Trump will pardon Hunter Biden before Jan 20, 2025 inauguration",
  "context": "Polymarket disputed market, settlement date 2025-01-19",
  "max_items_per_agent": 5
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| market_id | string | ✅ | 市场唯一标识 |
| claim | string | ✅ | 待核查的事实陈述 |
| context | string | ❌ | 额外背景信息（帮助 Agent 提升搜索精度） |
| max_items_per_agent | int | ❌ | 每个 Agent 最多返回条数，默认 5，范围 1-20 |

---

## 3. 响应格式（调查层 → 下游）

```json
{
  "success": true,
  "market_id": "pm_001",
  "evidence_pool": {
    "market_id": "pm_001",
    "claim": "Trump will pardon Hunter Biden before Jan 20, 2025 inauguration",
    "yes_weight": 1.76,
    "no_weight": 1.64,
    "total_items": 18,
    "items": [
      {
        "id": "official_web_0_a3b2c1",
        "source_type": "official",
        "source_name": "whitehouse.gov",
        "url": "https://www.whitehouse.gov/...",
        "title": "White House Statement on Pardons",
        "summary": "Biden White House confirms no preemptive pardon for Hunter Biden.",
        "raw_snippet": "The White House stated on January 10 that...",
        "direction": "supports_no",
        "confidence": 0.96,
        "relevance": 0.95,
        "weight": 0.912,
        "published_at": "2025-01-10T14:00:00Z",
        "agent": "OfficialAgent"
      },
      ...
    ]
  }
}
```

### EvidenceItem 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 唯一 ID，格式 `{agent_type}_{index}_{hex}` |
| source_type | enum | `social` / `news` / `official` / `counter` |
| source_name | string | 来源名称（媒体名、账号名、域名） |
| url | string | 原始链接 |
| title | string | 文章标题 / 推文标题 |
| summary | string | LLM 提炼摘要，≤120 字 |
| raw_snippet | string | 原始文本片段，≤300 字 |
| direction | enum | `supports_yes` / `supports_no` / `neutral` |
| confidence | float | 来源可信度，0-1，见下表 |
| relevance | float | 与 claim 相关度，LLM 打分，0-1 |
| weight | float | `confidence × relevance`，Bayesian 聚合直接使用 |
| published_at | string | ISO 8601，可为空 |
| agent | string | 产出该条证据的 Agent 名称 |

### confidence 打分规则（evidence_scoring.py）

| 来源类型 | confidence |
|---------|-----------|
| 政府官网（*.gov） | 0.96 |
| Reuters / AP | 0.91-0.92 |
| BBC / NYT / WaPo | 0.85-0.88 |
| 知名媒体（Politico等） | 0.75-0.82 |
| 官方认证 X 账号（高互动） | 0.70-0.72 |
| 认证 X 账号（低互动） | 0.58-0.65 |
| 未认证 X 账号（高互动） | 0.45-0.55 |
| 未知来源 | 0.30-0.40 |

### direction 枚举

| 值 | 含义 |
|----|------|
| `supports_yes` | 该证据支持事件发生（YES 方向） |
| `supports_no` | 该证据反对事件发生（NO 方向） |
| `neutral` | 中性，不明确支持任一方 |

---

## 4. Deliberation Engine 对接方式（给 Owner）

```python
from backend.investigation import run_investigation, InvestigationRequest

pool = run_investigation(InvestigationRequest(
    market_id="pm_001",
    claim="Trump will pardon Hunter Biden before Jan 20, 2025",
))

# 直接使用汇总权重做 Bayesian 先验
yes_prior = pool.yes_weight / (pool.yes_weight + pool.no_weight)

# 按 direction 过滤传给 Prosecutor / Defense Agent
yes_evidence = [i for i in pool.items if i.direction == "supports_yes"]
no_evidence  = [i for i in pool.items if i.direction == "supports_no"]

# 每条 EvidenceItem 已含 weight，可直接加权
```

---

## 5. xAPI 使用说明（hackathon 亮点）

xAPI（xapi.to）作为整个 Agent Network 的 X/Twitter 数据基础设施：

- **SocialAgent**：搜索 claim 相关的高互动推文，判断民众舆论方向
- **OfficialAgent**：搜索白宫、司法部等官方账号的相关推文，获取权威声明
- 所有 xAPI 调用集中在 `backend/xapi/client.py`，统一认证和错误处理
- Demo 演示可配合 `backend/investigation/mock_data.py` 的预缓存数据 fallback

申请 Token：https://www.xapi.to/

---

## 6. 本地启动

```bash
cd truth-oracle
cp .env.example .env   # 填入三个 API Key
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000

# 测试接口
curl -X POST http://localhost:8000/api/investigation/run \
  -H "Content-Type: application/json" \
  -d '{"market_id":"pm_001","claim":"Trump will pardon Hunter Biden before Jan 20 2025"}'
```

---

## 7. 文件结构

```
truth-oracle/backend/
├── main.py
├── xapi/
│   └── client.py              # xAPI (xapi.to) 封装
├── investigation/
│   ├── schema.py              # 数据契约（EvidenceItem / EvidencePool）
│   ├── evidence_scoring.py    # 可信度打分规则
│   ├── pipeline.py            # LangGraph 并行调度
│   ├── mock_data.py           # Demo fallback 数据
│   └── agents/
│       ├── social_agent.py    # xAPI → X/Twitter 证据
│       ├── news_agent.py      # Brave Search → 新闻证据
│       ├── official_agent.py  # xAPI + Brave → 官方声明
│       └── counter_agent.py   # Brave + LLM → 反驳证据
└── api/
    └── investigation_routes.py  # FastAPI 路由
```
