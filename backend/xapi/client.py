"""
xAPI Client — 封装 xapi.to 的 Twitter/X 数据接口

xapi.to 提供与 Twitter API v2 兼容的代理端点，无需申请 Elevated Access。
文档参考：https://www.xapi.to/
"""

import os
import httpx
from typing import Optional


XAPI_BASE_URL = "https://api.xapi.to/v2"
XAPI_TOKEN    = os.getenv("XAPI_TOKEN", "")   # 在 .env 中配置


class XAPIClient:
    """xapi.to 客户端（同步 / 异步均支持）"""

    def __init__(self, token: str = XAPI_TOKEN, timeout: int = 15):
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        self.timeout = timeout

    # ──────────────────────────────────────────
    # 搜索推文（Recent Search）
    # xapi.to endpoint: GET /v2/tweets/search/recent
    # ──────────────────────────────────────────
    def search_tweets(
        self,
        query: str,
        max_results: int = 10,
        tweet_fields: str = "created_at,author_id,public_metrics,source",
        expansions: str = "author_id",
        user_fields: str = "username,name,verified,public_metrics",
    ) -> dict:
        """
        搜索最近7天的推文。
        query 支持 Twitter 高级搜索语法，例如：
          - 'Trump Hunter Biden pardon -is:retweet lang:en'
          - 'from:WhiteHouse Biden pardon'
        """
        params = {
            "query": query,
            "max_results": min(max_results, 100),
            "tweet.fields": tweet_fields,
            "expansions": expansions,
            "user.fields": user_fields,
        }
        with httpx.Client(headers=self.headers, timeout=self.timeout) as client:
            resp = client.get(f"{XAPI_BASE_URL}/tweets/search/recent", params=params)
            resp.raise_for_status()
            return resp.json()

    # ──────────────────────────────────────────
    # 获取单条推文
    # ──────────────────────────────────────────
    def get_tweet(self, tweet_id: str) -> dict:
        params = {
            "tweet.fields": "created_at,author_id,public_metrics,text",
            "expansions": "author_id",
            "user.fields": "username,verified",
        }
        with httpx.Client(headers=self.headers, timeout=self.timeout) as client:
            resp = client.get(f"{XAPI_BASE_URL}/tweets/{tweet_id}", params=params)
            resp.raise_for_status()
            return resp.json()

    # ──────────────────────────────────────────
    # 按用户获取最近推文（用于 Official Agent）
    # ──────────────────────────────────────────
    def get_user_tweets(self, user_id: str, max_results: int = 5) -> dict:
        params = {
            "max_results": max_results,
            "tweet.fields": "created_at,public_metrics,text",
        }
        with httpx.Client(headers=self.headers, timeout=self.timeout) as client:
            resp = client.get(f"{XAPI_BASE_URL}/users/{user_id}/tweets", params=params)
            resp.raise_for_status()
            return resp.json()

    # ──────────────────────────────────────────
    # 按用户名查 user_id
    # ──────────────────────────────────────────
    def get_user_by_username(self, username: str) -> dict:
        params = {"user.fields": "id,name,username,verified,public_metrics"}
        with httpx.Client(headers=self.headers, timeout=self.timeout) as client:
            resp = client.get(f"{XAPI_BASE_URL}/users/by/username/{username}", params=params)
            resp.raise_for_status()
            return resp.json()

    # ──────────────────────────────────────────
    # 工具方法：从 search 响应提取结构化推文列表
    # ──────────────────────────────────────────
    @staticmethod
    def parse_search_results(raw: dict) -> list[dict]:
        """
        返回 list of:
        {
          "id": "...",
          "text": "...",
          "created_at": "...",
          "author_username": "...",
          "author_verified": bool,
          "like_count": int,
          "retweet_count": int,
          "url": "https://x.com/..."
        }
        """
        tweets = raw.get("data", [])
        users  = {u["id"]: u for u in raw.get("includes", {}).get("users", [])}

        results = []
        for t in tweets:
            author = users.get(t.get("author_id", ""), {})
            metrics = t.get("public_metrics", {})
            results.append({
                "id":               t["id"],
                "text":             t["text"],
                "created_at":       t.get("created_at", ""),
                "author_username":  author.get("username", "unknown"),
                "author_verified":  author.get("verified", False),
                "like_count":       metrics.get("like_count", 0),
                "retweet_count":    metrics.get("retweet_count", 0),
                "url":              f"https://x.com/{author.get('username','i')}/status/{t['id']}",
            })
        return results
