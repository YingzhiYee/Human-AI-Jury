"""
Investigation Layer Pipeline — LangGraph 并行调度四个 Agent

图结构：
  START
    │
    ├─── SocialAgent   ──┐
    ├─── NewsAgent     ──┤
    ├─── OfficialAgent ──┤──► merge ──► score ──► END
    └─── CounterAgent  ──┘

所有 Agent 并行运行（langgraph Send API），merge 节点汇聚后统一打分。
"""

from __future__ import annotations
import asyncio
from typing import TypedDict, Annotated, Optional
import operator

from langgraph.graph import StateGraph, START, END
from langgraph.constants import Send

from .schema import (
    InvestigationRequest,
    EvidencePool,
    EvidenceItem,
)
from .evidence_scoring import finalize_items
from .agents import news_agent, social_agent, official_agent, counter_agent
from .simulated_pool import build_simulated_pool


# ────────────────────────────────────────────
# LangGraph State
# ────────────────────────────────────────────

class InvestigationState(TypedDict):
    request: InvestigationRequest
    # 各 Agent 结果用 Annotated + operator.add 自动合并（reduce）
    items: Annotated[list[EvidenceItem], operator.add]
    pool: Optional[EvidencePool]


# ────────────────────────────────────────────
# Agent 节点（每个节点独立运行）
# ────────────────────────────────────────────

def node_social(state: InvestigationState) -> dict:
    req = state["request"]
    items = social_agent.run(req.claim, max_items=req.max_items_per_agent)
    return {"items": items}


def node_news(state: InvestigationState) -> dict:
    req = state["request"]
    items = news_agent.run(req.claim, max_items=req.max_items_per_agent)
    return {"items": items}


def node_official(state: InvestigationState) -> dict:
    req = state["request"]
    items = official_agent.run(req.claim, max_items=req.max_items_per_agent)
    return {"items": items}


def node_counter(state: InvestigationState) -> dict:
    req = state["request"]
    items = counter_agent.run(req.claim, max_items=req.max_items_per_agent)
    return {"items": items}


# ────────────────────────────────────────────
# 汇聚节点：打分 + 构建 EvidencePool
# ────────────────────────────────────────────

def node_merge_and_score(state: InvestigationState) -> dict:
    req   = state["request"]
    items = finalize_items(state.get("items", []))

    pool = EvidencePool(
        market_id=req.market_id,
        claim=req.claim,
        items=items,
    )
    pool.compute_summary()
    return {"pool": pool}


# ────────────────────────────────────────────
# 构建 LangGraph
# ────────────────────────────────────────────

def _build_graph() -> StateGraph:
    g = StateGraph(InvestigationState)

    g.add_node("social",  node_social)
    g.add_node("news",    node_news)
    g.add_node("official",node_official)
    g.add_node("counter", node_counter)
    g.add_node("merge",   node_merge_and_score)

    # 并行触发四个 Agent
    g.add_edge(START,     "social")
    g.add_edge(START,     "news")
    g.add_edge(START,     "official")
    g.add_edge(START,     "counter")

    # 全部完成后汇聚
    g.add_edge("social",  "merge")
    g.add_edge("news",    "merge")
    g.add_edge("official","merge")
    g.add_edge("counter", "merge")

    g.add_edge("merge", END)
    return g


_graph = _build_graph().compile()


# ────────────────────────────────────────────
# 公开接口
# ────────────────────────────────────────────

def run_investigation(request: InvestigationRequest) -> EvidencePool:
    """
    同步入口（FastAPI 背景线程 / 直接调用均可）

    示例：
        pool = run_investigation(InvestigationRequest(
            market_id="pm_001",
            claim="Trump will pardon Hunter Biden before Jan 20",
        ))
    """
    init_state: InvestigationState = {
        "request": request,
        "items": [],
        "pool": None,
    }
    final = _graph.invoke(init_state)
    pool  = final.get("pool")
    if pool is None:
        raise RuntimeError("Investigation pipeline returned no EvidencePool")
    if not pool.items:
        return build_simulated_pool(request)
    return pool


async def run_investigation_async(request: InvestigationRequest) -> EvidencePool:
    """异步入口（可在 async FastAPI 路由中 await）"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, run_investigation, request)
