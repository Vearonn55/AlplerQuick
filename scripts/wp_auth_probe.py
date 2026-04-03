#!/usr/bin/env python3
"""Probe WordPress REST auth (GET /users/me). Logs NDJSON for debug; never logs secrets."""

from __future__ import annotations

import asyncio
import base64
import json
import os
import sys
import time
from pathlib import Path

import httpx

# Running as `python scripts/wp_auth_probe.py` puts `scripts/` on sys.path, not project root.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# region agent log
_SESSION = "3a85d6"
_LOG = Path(
    os.environ.get(
        "ALPLER_DEBUG_LOG",
        str(Path(__file__).resolve().parent.parent / ".cursor" / "debug-3a85d6.log"),
    )
)


def _dbg(hypothesis_id: str, message: str, data: dict) -> None:
    _LOG.parent.mkdir(parents=True, exist_ok=True)
    line = {
        "sessionId": _SESSION,
        "timestamp": int(time.time() * 1000),
        "hypothesisId": hypothesis_id,
        "location": "scripts/wp_auth_probe.py",
        "message": message,
        "data": data,
        "runId": os.environ.get("ALPLER_PROBE_RUN", "probe1"),
    }
    with _LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")


# endregion agent log


async def main() -> None:
    from dotenv import load_dotenv

    load_dotenv()
    from src.config import load_settings

    settings = load_settings()
    base = settings.wp_base_url.rstrip("/")
    user = settings.wp_username
    pw = settings.wp_application_password
    url = f"{base}/wp-json/wp/v2/users/me"
    headers = {
        "User-Agent": f"Mozilla/5.0 (compatible; AlplerQuick/1.0; +{base})",
    }

    _dbg(
        "H2",
        "env_shape",
        {
            "wp_base_url_host": base.split("://", 1)[-1].split("/")[0],
            "username_len": len(user),
            "password_len": len(pw),
        },
    )

    # H1/H2: same as bot — httpx basic auth
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers=headers) as client:
        r1 = await client.get(url, auth=(user, pw))
    j1: dict = {}
    try:
        j1 = r1.json() if r1.content else {}
    except Exception:
        j1 = {"_parse_error": True}
    _dbg(
        "H1",
        "users_me_httpx_auth",
        {
            "status": r1.status_code,
            "final_url": str(r1.url),
            "wp_code": j1.get("code"),
            "sent_auth_via": "httpx.BasicAuth",
        },
    )

    # H3: explicit Authorization header (detect proxy stripping oddities)
    token = base64.b64encode(f"{user}:{pw}".encode()).decode("ascii")
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers=headers) as client:
        r2 = await client.get(url, headers={**headers, "Authorization": f"Basic {token}"})
    j2: dict = {}
    try:
        j2 = r2.json() if r2.content else {}
    except Exception:
        j2 = {"_parse_error": True}
    _dbg(
        "H3",
        "users_me_explicit_basic_header",
        {
            "status": r2.status_code,
            "final_url": str(r2.url),
            "wp_code": j2.get("code"),
            "same_as_httpx_auth": r1.status_code == r2.status_code and j1.get("code") == j2.get("code"),
        },
    )

    print("httpx auth:", r1.status_code, j1.get("code", j1.get("id", "")))
    print("header auth:", r2.status_code, j2.get("code", j2.get("id", "")))
    print("NDJSON log:", _LOG)


if __name__ == "__main__":
    asyncio.run(main())
