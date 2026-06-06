"""Runtime settings and environment loading helpers."""

from __future__ import annotations

import os
import platform
import sys
import tomllib
from importlib.util import find_spec
from pathlib import Path

import httpx
from dotenv import dotenv_values, find_dotenv, load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
_loaded_env_file: str | None = None
_loaded_env_values: dict[str, str] = {}
_loaded_codex_config: dict[str, object] | None = None


def _clean_env_value(value: str) -> str:
    """Strip whitespace and accidental wrapping quotes from pasted secrets."""
    value = value.strip()
    return value.strip("\"'“”‘’")


def ensure_env_loaded() -> str | None:
    """Load a local .env file once so agent modules see real credentials."""
    global _loaded_env_file, _loaded_env_values
    if _loaded_env_file is not None:
        return _loaded_env_file or None

    env_path = find_dotenv(filename=".env", usecwd=True)
    if not env_path:
        candidate = ROOT_DIR / ".env"
        env_path = str(candidate) if candidate.exists() else ""

    if env_path:
        _loaded_env_values = {
            key: _clean_env_value(value)
            for key, value in dotenv_values(env_path).items()
            if value is not None
        }
        for key, value in _loaded_env_values.items():
            os.environ[key] = value
        load_dotenv(env_path, override=True)
        _loaded_env_file = env_path
    else:
        _loaded_env_file = ""

    return _loaded_env_file or None


def get_env(name: str, default: str = "") -> str:
    """Read a runtime secret after .env normalization."""
    ensure_env_loaded()
    value = os.getenv(name)
    if value is not None:
        return _clean_env_value(value)
    if name in _loaded_env_values:
        return _loaded_env_values[name]
    return default


def _load_codex_config() -> dict[str, object]:
    global _loaded_codex_config
    if _loaded_codex_config is not None:
        return _loaded_codex_config

    config_path = Path.home() / ".codex" / "config.toml"
    if not config_path.exists():
        _loaded_codex_config = {}
        return _loaded_codex_config

    try:
        _loaded_codex_config = tomllib.loads(config_path.read_text())
    except Exception:
        _loaded_codex_config = {}
    return _loaded_codex_config


def _selected_codex_provider() -> dict[str, object]:
    config = _load_codex_config()
    provider_name = str(config.get("model_provider", "") or "")
    providers = config.get("model_providers", {})
    if not isinstance(providers, dict) or not provider_name:
        return {}
    provider = providers.get(provider_name, {})
    return provider if isinstance(provider, dict) else {}


def get_openai_base_url(default: str = "") -> str:
    env_value = get_env("OPENAI_BASE_URL") or get_env("OPENAI_API_BASE")
    if env_value:
        return env_value
    provider = _selected_codex_provider()
    base_url = provider.get("base_url", "")
    return _clean_env_value(str(base_url)) if base_url else default


def get_openai_model(default: str = "gpt-4o-mini") -> str:
    env_value = get_env("OPENAI_MODEL") or get_env("OPENAI_CHAT_MODEL")
    if env_value:
        return env_value

    config = _load_codex_config()
    model = _clean_env_value(str(config.get("model", "") or ""))
    base_url = get_openai_base_url("")

    # PackyAPI's listed default model may require Responses API, while our
    # backend currently uses chat completions. Use the verified chat-capable
    # sibling model unless the user explicitly overrides it via env.
    if "packyapi.com" in base_url and model == "gpt-5.4":
        return "gpt-5.4-high"

    return model or default


def build_openai_client(timeout: float = 20.0):
    from openai import OpenAI

    kwargs: dict[str, object] = {
        "api_key": get_env("OPENAI_API_KEY", ""),
        "timeout": timeout,
    }
    base_url = get_openai_base_url("")
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs)


def _has_env(name: str) -> bool:
    value = get_env(name).strip()
    return bool(value) and "your_" not in value and "placeholder" not in value


def _trim_error(exc: Exception) -> str:
    return str(exc).strip().replace("\n", " ")[:240]


def _check_openai() -> dict[str, object]:
    if not _has_env("OPENAI_API_KEY"):
        return {"ok": False, "detail": "missing"}
    try:
        model = get_openai_model()
        client = build_openai_client(timeout=10.0)
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Reply with OK"}],
            max_tokens=10,
            temperature=0,
        )
        if not resp.choices:
            raise RuntimeError("OpenAI-compatible provider returned no choices")
        return {
            "ok": True,
            "detail": f"authenticated via {get_openai_base_url('official')} model {model}",
        }
    except Exception as exc:
        return {"ok": False, "detail": _trim_error(exc)}


def _check_xapi() -> dict[str, object]:
    if not _has_env("XAPI_TOKEN"):
        return {"ok": False, "detail": "missing"}
    try:
        response = httpx.post(
            f"https://mcp.xapi.to/mcp?apikey={get_env('XAPI_TOKEN')}",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "human-ai-jury-readiness",
                        "version": "0.1.0",
                    },
                },
            },
            timeout=5,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("error"):
            raise RuntimeError(payload["error"].get("message", "xAPI initialize failed"))
        return {"ok": True, "detail": "authenticated"}
    except Exception as exc:
        return {"ok": False, "detail": _trim_error(exc)}


def _check_brave() -> dict[str, object]:
    if not _has_env("BRAVE_API_KEY"):
        return {"ok": False, "detail": "missing"}
    try:
        response = httpx.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={
                "Accept": "application/json",
                "X-Subscription-Token": get_env("BRAVE_API_KEY"),
            },
            params={"q": "human ai jury", "count": 1},
            timeout=5,
        )
        response.raise_for_status()
        return {"ok": True, "detail": "authenticated"}
    except Exception as exc:
        return {"ok": False, "detail": _trim_error(exc)}


def build_runtime_status(include_live_checks: bool = False) -> dict[str, object]:
    """Return a lightweight readiness snapshot for local debugging."""
    env_file = ensure_env_loaded()
    credentials = {
        "openai_api_key": _has_env("OPENAI_API_KEY"),
        "brave_api_key": _has_env("BRAVE_API_KEY"),
        "xapi_token": _has_env("XAPI_TOKEN"),
    }
    dependencies = {
        "langgraph": find_spec("langgraph") is not None,
        "openai": find_spec("openai") is not None,
        "httpx": find_spec("httpx") is not None,
        "python_dotenv": find_spec("dotenv") is not None,
    }
    provider_checks: dict[str, object] = {}
    live_investigation_ready = all(credentials.values()) and all(dependencies.values())
    if include_live_checks and live_investigation_ready:
        provider_checks = {
            "openai": _check_openai(),
            "brave": _check_brave(),
            "xapi": _check_xapi(),
        }
        live_investigation_ready = live_investigation_ready and all(
            bool(check.get("ok")) for check in provider_checks.values()
        )

    return {
        "env_file": env_file,
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "llm_runtime": {
            "base_url": get_openai_base_url("official"),
            "model": get_openai_model(),
        },
        "credentials": credentials,
        "dependencies": dependencies,
        "provider_checks": provider_checks,
        "live_investigation_ready": live_investigation_ready,
        "missing": {
            "credentials": [name for name, ok in credentials.items() if not ok],
            "dependencies": [name for name, ok in dependencies.items() if not ok],
        },
    }


ensure_env_loaded()
