"""Runtime settings and environment loading helpers."""

from __future__ import annotations

import os
import platform
import sys
from importlib.util import find_spec
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
_loaded_env_file: str | None = None


def ensure_env_loaded() -> str | None:
    """Load a local .env file once so agent modules see real credentials."""
    global _loaded_env_file
    if _loaded_env_file is not None:
        return _loaded_env_file or None

    env_path = find_dotenv(filename=".env", usecwd=True)
    if not env_path:
        candidate = ROOT_DIR / ".env"
        env_path = str(candidate) if candidate.exists() else ""

    if env_path:
        load_dotenv(env_path, override=False)
        _loaded_env_file = env_path
    else:
        _loaded_env_file = ""

    return _loaded_env_file or None


def _has_env(name: str) -> bool:
    value = os.getenv(name, "").strip()
    return bool(value) and "your_" not in value and "placeholder" not in value


def build_runtime_status() -> dict[str, object]:
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
    live_investigation_ready = all(credentials.values()) and all(dependencies.values())

    return {
        "env_file": env_file,
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "credentials": credentials,
        "dependencies": dependencies,
        "live_investigation_ready": live_investigation_ready,
        "missing": {
            "credentials": [name for name, ok in credentials.items() if not ok],
            "dependencies": [name for name, ok in dependencies.items() if not ok],
        },
    }


ensure_env_loaded()
