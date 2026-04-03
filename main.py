#!/usr/bin/env python3
"""Entry: Telegram bot for catalog PDFs → linearize → WordPress + catalogues page HTML."""

from __future__ import annotations

import logging
import sys

from src.bot_app import build_application
from src.config import load_settings


def main() -> None:
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        level=logging.INFO,
    )
    try:
        settings = load_settings()
    except ValueError as exc:
        logging.error("Configuration error: %s", exc)
        sys.exit(1)

    logging.info("WordPress REST base: %s/wp-json/wp/v2", settings.wp_base_url.rstrip("/"))

    application = build_application(settings)

    if settings.bot_mode == "webhook":
        webhook_url = f"{settings.webhook_base_url}{settings.webhook_path}"
        logging.info("Starting webhook on port %s path %s", settings.port, settings.webhook_path)
        application.run_webhook(
            listen="0.0.0.0",
            port=settings.port,
            url_path=settings.webhook_path.lstrip("/"),
            webhook_url=webhook_url,
            secret_token=settings.telegram_webhook_secret,
            allowed_updates=["message", "callback_query"],
        )
    else:
        logging.info("Starting polling")
        application.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
