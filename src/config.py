"""Load and validate configuration from environment."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    allowed_telegram_user_ids: frozenset[int]
    wp_base_url: str
    wp_username: str
    wp_application_password: str
    wp_page_id: int
    catalogues_config_path: Path
    bot_mode: str
    webhook_base_url: str | None
    webhook_path: str
    port: int
    telegram_webhook_secret: str | None


def _parse_user_ids(raw: str) -> frozenset[int]:
    ids: set[int] = set()
    for part in raw.replace(" ", "").split(","):
        if not part:
            continue
        ids.add(int(part))
    return frozenset(ids)


def _resolve_catalogues_path(raw: str) -> Path:
    path = Path(raw.strip())
    if not path.is_absolute():
        root = Path(__file__).resolve().parent.parent
        path = root / path
    return path


def load_settings() -> Settings:
    load_dotenv()
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN is required")

    ids_raw = os.environ.get("ALLOWED_TELEGRAM_USER_IDS", "").strip()
    if not ids_raw:
        raise ValueError("ALLOWED_TELEGRAM_USER_IDS is required (comma-separated)")
    allowed = _parse_user_ids(ids_raw)

    base = os.environ.get("WP_BASE_URL", "").strip().rstrip("/")
    if not base:
        raise ValueError("WP_BASE_URL is required")
    user = os.environ.get("WP_USERNAME", "").strip()
    if not user:
        raise ValueError("WP_USERNAME is required")
    app_pw = os.environ.get("WP_APPLICATION_PASSWORD", "").replace(" ", "").strip()
    if not app_pw:
        raise ValueError("WP_APPLICATION_PASSWORD is required")

    page_raw = os.environ.get("WP_PAGE_ID", "").strip()
    if not page_raw:
        raise ValueError("WP_PAGE_ID is required")
    page_id = int(page_raw)

    cat_cfg = os.environ.get("CATALOGUES_CONFIG", "catalogues.json").strip() or "catalogues.json"
    catalogues_path = _resolve_catalogues_path(cat_cfg)
    if not catalogues_path.is_file():
        raise ValueError(f"CATALOGUES_CONFIG file not found: {catalogues_path}")

    mode = os.environ.get("BOT_MODE", "polling").strip().lower()
    if mode not in ("polling", "webhook"):
        raise ValueError("BOT_MODE must be polling or webhook")

    wh_base = os.environ.get("WEBHOOK_BASE_URL", "").strip().rstrip("/") or None
    wh_path = os.environ.get("WEBHOOK_PATH", "/telegram/webhook").strip()
    if not wh_path.startswith("/"):
        wh_path = "/" + wh_path
    port = int(os.environ.get("PORT", "8080"))
    wh_secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "").strip() or None

    if mode == "webhook" and not wh_base:
        raise ValueError("WEBHOOK_BASE_URL is required when BOT_MODE=webhook")

    return Settings(
        telegram_bot_token=token,
        allowed_telegram_user_ids=allowed,
        wp_base_url=base,
        wp_username=user,
        wp_application_password=app_pw,
        wp_page_id=page_id,
        catalogues_config_path=catalogues_path,
        bot_mode=mode,
        webhook_base_url=wh_base,
        webhook_path=wh_path,
        port=port,
        telegram_webhook_secret=wh_secret,
    )
