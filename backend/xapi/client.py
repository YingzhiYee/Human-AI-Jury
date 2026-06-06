"""xAPI Client — use the current xAPI MCP endpoint for Twitter/X data."""

from __future__ import annotations

import json
import os

import httpx

XAPI_MCP_URL = "https://mcp.xapi.to/mcp"
XAPI_TOKEN = os.getenv("XAPI_TOKEN", "")


class XAPIClient:
    """Thin wrapper over xAPI's MCP endpoint for Twitter capability calls."""

    def __init__(self, token: str = XAPI_TOKEN, timeout: int = 20):
        self.token = token
        self.timeout = timeout
        self.base_url = f"{XAPI_MCP_URL}?apikey={token}"
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        self._initialized = False

    def _rpc(self, method: str, params: dict, request_id: int) -> dict:
        with httpx.Client(headers=self.headers, timeout=self.timeout) as client:
            response = client.post(
                self.base_url,
                json={
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "method": method,
                    "params": params,
                },
            )
            response.raise_for_status()
            payload = response.json()
            if payload.get("error"):
                raise RuntimeError(payload["error"].get("message", "xAPI RPC error"))
            return payload

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        self._rpc(
            "initialize",
            {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {
                    "name": "human-ai-jury-backend",
                    "version": "0.1.0",
                },
            },
            request_id=1,
        )
        self._initialized = True

    def _tool_call(self, tool_name: str, arguments: dict, request_id: int = 2) -> dict:
        self._ensure_initialized()
        payload = self._rpc(
            "tools/call",
            {
                "name": tool_name,
                "arguments": arguments,
            },
            request_id=request_id,
        )
        content = payload.get("result", {}).get("content", [])
        if not content:
            return {}

        if payload.get("result", {}).get("isError"):
            message = next(
                (item.get("text") for item in content if item.get("type") == "text"),
                "xAPI tool call failed",
            )
            raise RuntimeError(message)

        text_block = next((item.get("text") for item in content if item.get("type") == "text"), None)
        if not text_block:
            return {}

        try:
            parsed = json.loads(text_block)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"xAPI returned non-JSON content: {text_block}") from exc
        if isinstance(parsed, dict) and parsed.get("error"):
            raise RuntimeError(parsed["error"])
        return parsed

    def search_tweets(
        self,
        query: str,
        max_results: int = 10,
        tweet_fields: str = "created_at,author_id,public_metrics,source",
        expansions: str = "author_id",
        user_fields: str = "username,name,verified,public_metrics",
    ) -> dict:
        """Search tweets through the official twitter.search capability."""
        del tweet_fields, expansions, user_fields
        payload = self._tool_call(
            "CALL",
            {
                "action_id": "twitter.search",
                "arguments": {
                    "raw_query": query,
                    "sort_by": "Latest",
                    "provider": "x",
                },
            },
        )
        tweets = payload.get("data", {}).get("tweets", [])[: max_results]
        return {
            "data": {
                **payload.get("data", {}),
                "tweets": tweets,
            }
        }

    def get_tweet(self, tweet_id: str) -> dict:
        payload = self._tool_call(
            "CALL",
            {
                "action_id": "twitter.tweet_detail",
                "arguments": {
                    "focalTweetId": tweet_id,
                    "provider": "x",
                },
            },
        )
        return payload

    def get_user_tweets(self, user_id: str, max_results: int = 5) -> dict:
        payload = self._tool_call(
            "CALL",
            {
                "action_id": "twitter.user_tweets",
                "arguments": {
                    "user_id": user_id,
                    "provider": "x",
                },
            },
        )
        tweets = payload.get("data", {}).get("tweets", [])[: max_results]
        return {
            "data": {
                **payload.get("data", {}),
                "tweets": tweets,
            }
        }

    def get_user_by_username(self, username: str) -> dict:
        payload = self._tool_call(
            "CALL",
            {
                "action_id": "twitter.user_by_screen_name",
                "arguments": {
                    "screen_name": username.lstrip("@"),
                    "provider": "x",
                },
            },
        )
        return payload

    @staticmethod
    def parse_search_results(raw: dict) -> list[dict]:
        """
        Return a normalized list of tweet dicts used by the investigation agents.

        Supports both:
        - legacy Twitter-v2-like payloads
        - current xAPI twitter.search MCP payloads
        """
        if isinstance(raw.get("data"), list):
            tweets = raw.get("data", [])
            users = {u["id"]: u for u in raw.get("includes", {}).get("users", [])}
            results = []
            for tweet in tweets:
                author = users.get(tweet.get("author_id", ""), {})
                metrics = tweet.get("public_metrics", {})
                username = author.get("username", "unknown")
                results.append(
                    {
                        "id": tweet["id"],
                        "text": tweet["text"],
                        "created_at": tweet.get("created_at", ""),
                        "author_username": username,
                        "author_verified": author.get("verified", False),
                        "like_count": metrics.get("like_count", 0),
                        "retweet_count": metrics.get("retweet_count", 0),
                        "url": f"https://x.com/{username}/status/{tweet['id']}",
                    }
                )
            return results

        tweets = raw.get("data", {}).get("tweets", [])
        results = []
        for tweet in tweets:
            user = tweet.get("user", {})
            username = user.get("screen_name", "unknown")
            results.append(
                {
                    "id": tweet.get("tweet_id", ""),
                    "text": tweet.get("text", ""),
                    "created_at": tweet.get("created_at", ""),
                    "author_username": username,
                    "author_verified": user.get("verified", False),
                    "like_count": tweet.get("favorite_count", 0),
                    "retweet_count": tweet.get("retweet_count", 0),
                    "url": f"https://x.com/{username}/status/{tweet.get('tweet_id', '')}",
                }
            )
        return results
