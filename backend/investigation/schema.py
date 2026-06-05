"""
Investigation Layer — 数据契约（与上下游的接口规范）

上游（API / Deliberation Engine）传入 InvestigationRequest
下游（Deliberation Engine）消费 EvidencePool
"""

from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


# ────────────────────────────────────────────
# 枚举
# ────────────────────────────────────────────

class EvidenceDirection(str, Enum):
    SUPPORTS_YES = "supports_yes"
    SUPPORTS_NO  = "supports_no"
    NEUTRAL      = "neutral"

class SourceType(str, Enum):
    SOCIAL   = "social"    # X / Twitter
    NEWS     = "news"      # 新闻媒体
    OFFICIAL = "official"  # 政府 / 机构官方声明
    COUNTER  = "counter"   # 反驳证据


# ────────────────────────────────────────────
# 核心数据结构
# ────────────────────────────────────────────

class EvidenceItem(BaseModel):
    """单条证据，由各 Agent 产出，汇入 EvidencePool"""

    id: str = Field(..., description="唯一 ID，格式: {source_type}_{index}")
    source_type: SourceType
    source_name: str            # e.g. "Reuters", "@elonmusk", "whitehouse.gov"
    url: str
    title: str
    summary: str                # Agent 提炼的摘要，≤120 字
    raw_snippet: str            # 原始文本片段
    direction: EvidenceDirection
    confidence: float = Field(..., ge=0.0, le=1.0,
                              description="来源可信度分 0-1，见 evidence_scoring.py 计算规则")
    relevance: float  = Field(..., ge=0.0, le=1.0,
                              description="与 claim 的相关度，由 LLM 评估")
    weight: float     = Field(default=0.0,
                              description="confidence × relevance，Bayesian 聚合使用")
    published_at: Optional[str] = None   # ISO 8601
    agent: str = ""                      # 产出该条证据的 Agent 名称


class EvidencePool(BaseModel):
    """Investigation Layer 最终输出，传给 Deliberation Engine"""

    market_id: str
    claim: str
    items: list[EvidenceItem]

    # 汇总统计（Deliberation Engine 可直接使用）
    yes_weight: float = 0.0
    no_weight:  float = 0.0
    total_items: int  = 0

    def compute_summary(self) -> None:
        """汇总前调用一次即可"""
        yes = sum(i.weight for i in self.items if i.direction == EvidenceDirection.SUPPORTS_YES)
        no  = sum(i.weight for i in self.items if i.direction == EvidenceDirection.SUPPORTS_NO)
        self.yes_weight  = round(yes, 4)
        self.no_weight   = round(no, 4)
        self.total_items = len(self.items)


# ────────────────────────────────────────────
# 请求 / 响应
# ────────────────────────────────────────────

class InvestigationRequest(BaseModel):
    """
    上游传入格式（FastAPI endpoint 或 Deliberation Engine 直接调用）

    示例：
    {
      "market_id": "pm_001",
      "claim": "Trump will pardon Hunter Biden before Jan 20, 2025 inauguration",
      "context": "Polymarket market, deadline 2025-01-19",
      "max_items_per_agent": 5
    }
    """
    market_id: str
    claim: str
    context: str = ""
    max_items_per_agent: int = Field(default=5, ge=1, le=20)


class InvestigationResponse(BaseModel):
    """FastAPI 返回给前端 / 其他服务的响应包"""
    success: bool
    market_id: str
    evidence_pool: Optional[EvidencePool] = None
    error: Optional[str] = None
