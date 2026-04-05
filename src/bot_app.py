"""Telegram: pick catalogue → send PDF → linearize → WP media + HTML href update."""

from __future__ import annotations

import asyncio
import logging
import unicodedata

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import BadRequest
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

from src.catalogues import CatalogueEntry, by_id, load_catalogues
from src.config import Settings
from src.i18n import USER_DATA_LOCALE, effective_locale, locale_from_telegram, t
from src.html_replace import HrefReplaceError, replace_href_by_selector
from src.pdf_linearize import LinearizeError, linearize_pdf_bytes
from src.wp_client import WordPressClient, WordPressError

logger = logging.getLogger(__name__)

PDF_MIME = "application/pdf"
CALLBACK_PREFIX = "c:"
LANG_CALLBACK_PREFIX = "lang:"
USER_DATA_CATALOG = "pending_catalog_id"
# Telegram Bot API (api.telegram.org) refuses downloads over this size.
TELEGRAM_BOT_MAX_DOWNLOAD_BYTES = 20 * 1024 * 1024


def _is_pdf_document(update: Update) -> bool:
    doc = update.message.document
    if not doc:
        return False
    if doc.mime_type and doc.mime_type.lower() == PDF_MIME:
        return True
    name = (doc.file_name or "").lower()
    return name.endswith(".pdf")


def _catalogue_keyboard(entries: list[CatalogueEntry]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(e.label, callback_data=f"{CALLBACK_PREFIX}{e.id}")] for e in entries]
    return InlineKeyboardMarkup(rows)


def _authorized(user_id: int | None, settings: Settings) -> bool:
    return user_id is not None and user_id in settings.allowed_telegram_user_ids


def _fold_ascii(s: str) -> str:
    """Lowercase for language aliases; strips combining marks so Turkish input matches reliably."""
    s = unicodedata.normalize("NFKD", s.strip())
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


def _parse_lang_arg(raw: str) -> str | None:
    f = _fold_ascii(raw)
    if f in ("en", "english", "ingilizce"):
        return "en"
    if f in ("tr", "turkish", "turkce"):
        return "tr"
    if f in ("auto", "otomatik", "reset", "telegram"):
        return "auto"
    return None


def _apply_language_choice(context: ContextTypes.DEFAULT_TYPE, choice: str) -> None:
    if choice == "en":
        context.user_data[USER_DATA_LOCALE] = "en"
    elif choice == "tr":
        context.user_data[USER_DATA_LOCALE] = "tr"
    elif choice == "auto":
        context.user_data.pop(USER_DATA_LOCALE, None)


def _language_menu_text(context: ContextTypes.DEFAULT_TYPE, user, loc: str) -> str:
    override = context.user_data.get(USER_DATA_LOCALE)
    lines = [t(loc, "language_menu_intro"), ""]
    if override in ("en", "tr"):
        lines.append(t(loc, "language_menu_fixed", lang=t(loc, f"lang_{override}")))
    else:
        auto = locale_from_telegram(user)
        lines.append(t(loc, "language_menu_from_tg", lang=t(loc, f"lang_{auto}")))
    lines.extend(["", t(loc, "language_menu_hint")])
    return "\n".join(lines)


def _language_keyboard(loc: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(t(loc, "language_btn_en"), callback_data=f"{LANG_CALLBACK_PREFIX}en"),
                InlineKeyboardButton(t(loc, "language_btn_tr"), callback_data=f"{LANG_CALLBACK_PREFIX}tr"),
            ],
            [InlineKeyboardButton(t(loc, "language_btn_auto"), callback_data=f"{LANG_CALLBACK_PREFIX}auto")],
        ]
    )


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    loc = effective_locale(context, update.effective_user)
    await update.message.reply_text(t(loc, "start"))


async def cmd_catalogues(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.bot_data["settings"]
    loc = effective_locale(context, update.effective_user)
    if not _authorized(update.effective_user.id if update.effective_user else None, settings):
        await update.message.reply_text(t(loc, "not_authorized"))
        return
    entries: list[CatalogueEntry] = context.bot_data["catalogues"]
    await update.message.reply_text(
        t(loc, "catalogues_prompt"),
        reply_markup=_catalogue_keyboard(entries),
    )


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.bot_data["settings"]
    loc = effective_locale(context, update.effective_user)
    if not _authorized(update.effective_user.id if update.effective_user else None, settings):
        await update.message.reply_text(t(loc, "not_authorized"))
        return
    context.user_data.pop(USER_DATA_CATALOG, None)
    await update.message.reply_text(t(loc, "cancel_cleared"))


async def on_catalogue_pick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return
    await query.answer()
    settings: Settings = context.bot_data["settings"]
    loc = effective_locale(context, query.from_user)
    if not _authorized(query.from_user.id if query.from_user else None, settings):
        await query.edit_message_text(t(loc, "callback_not_authorized"))
        return
    data = query.data or ""
    if not data.startswith(CALLBACK_PREFIX):
        return
    cat_id = data[len(CALLBACK_PREFIX) :]
    cmap: dict[str, CatalogueEntry] = context.bot_data["catalogues_by_id"]
    entry = cmap.get(cat_id)
    if not entry:
        await query.edit_message_text(t(loc, "unknown_catalogue"))
        return
    context.user_data[USER_DATA_CATALOG] = cat_id
    await query.edit_message_text(t(loc, "selected_catalog", label=entry.label))


async def on_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.bot_data["settings"]
    wp: WordPressClient = context.bot_data["wp_client"]
    cmap: dict[str, CatalogueEntry] = context.bot_data["catalogues_by_id"]

    user = update.effective_user
    loc = effective_locale(context, user)
    if not _authorized(user.id if user else None, settings):
        logger.info("Rejected document from unauthorized user id=%s", user.id if user else None)
        await update.message.reply_text(t(loc, "not_authorized_upload"))
        return

    cat_id = context.user_data.get(USER_DATA_CATALOG)
    if not cat_id:
        await update.message.reply_text(t(loc, "document_no_catalog"))
        return

    entry = cmap.get(cat_id)
    if not entry:
        context.user_data.pop(USER_DATA_CATALOG, None)
        await update.message.reply_text(t(loc, "invalid_selection"))
        return

    if not _is_pdf_document(update):
        await update.message.reply_text(t(loc, "send_pdf_document"))
        return

    doc = update.message.document
    if doc.file_size is not None and doc.file_size > TELEGRAM_BOT_MAX_DOWNLOAD_BYTES:
        await update.message.reply_text(
            t(loc, "file_too_large", size_mb=doc.file_size / (1024 * 1024)),
        )
        return

    await update.message.reply_text(t(loc, "downloading"))

    try:
        tg_file = await context.bot.get_file(doc.file_id)
        data = await tg_file.download_as_bytearray()
        file_bytes = bytes(data)
    except Exception as exc:
        logger.exception("Telegram download failed")
        msg = f"Could not download file from Telegram: {exc}"
        if "too big" in str(exc).lower() or "too large" in str(exc).lower():
            msg += t(loc, "download_failed_suffix")
        await update.message.reply_text(msg)
        return

    await update.message.reply_text(t(loc, "linearizing"))
    try:
        linearized = await asyncio.to_thread(linearize_pdf_bytes, file_bytes)
    except LinearizeError as exc:
        await update.message.reply_text(t(loc, "linearize_failed", error=str(exc)))
        return

    filename = entry.upload_filename
    if not filename.lower().endswith(".pdf"):
        filename = f"{filename}.pdf"

    await update.message.reply_text(t(loc, "uploading_wp"))
    try:
        media = await wp.upload_media(linearized, filename)
        source_url = media.get("source_url") or media.get("link") or ""
        if not source_url:
            raise WordPressError("Upload succeeded but no source_url in response")

        raw = await wp.get_page_raw_content(settings.wp_page_id)
        updated = replace_href_by_selector(raw, entry.selector, source_url)
        await wp.patch_page_raw_content(settings.wp_page_id, updated)
    except (WordPressError, HrefReplaceError) as exc:
        await update.message.reply_text(t(loc, "wp_html_error", error=str(exc)))
        return
    except Exception as exc:
        logger.exception("Unexpected error during WordPress update")
        await update.message.reply_text(t(loc, "unexpected_error", error=str(exc)))
        return

    context.user_data.pop(USER_DATA_CATALOG, None)
    await update.message.reply_text(t(loc, "done", label=entry.label, url=source_url))


async def on_plain_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Nudge users who type instead of following the PDF flow."""
    settings: Settings = context.bot_data["settings"]
    loc = effective_locale(context, update.effective_user)
    if not _authorized(update.effective_user.id if update.effective_user else None, settings):
        await update.message.reply_text(t(loc, "not_authorized"))
        return
    await update.message.reply_text(t(loc, "plain_text_nudge"))


async def on_language_pick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return
    data = query.data or ""
    choice = data[len(LANG_CALLBACK_PREFIX) :] if data.startswith(LANG_CALLBACK_PREFIX) else ""
    if choice not in ("en", "tr", "auto"):
        await query.answer()
        return
    user = query.from_user
    _apply_language_choice(context, choice)
    loc = effective_locale(context, user)
    toast_key = "language_toast_auto" if choice == "auto" else f"language_toast_{choice}"
    await query.answer(t(loc, toast_key)[:200])
    body = _language_menu_text(context, user, loc)
    try:
        await query.edit_message_text(body, reply_markup=_language_keyboard(loc))
    except BadRequest as exc:
        if "message is not modified" not in str(exc).lower():
            raise


async def cmd_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    user = update.effective_user
    loc_before = effective_locale(context, user)
    args = context.args or []
    parsed_any = False
    for raw in args:
        choice = _parse_lang_arg(raw)
        if choice:
            _apply_language_choice(context, choice)
            parsed_any = True
            break
    loc = effective_locale(context, user)
    body = _language_menu_text(context, user, loc)
    if args and not parsed_any:
        body = t(loc_before, "language_help_unknown") + "\n\n" + body
    await update.message.reply_text(body, reply_markup=_language_keyboard(loc))


def build_application(settings: Settings) -> Application:
    entries = load_catalogues(settings.catalogues_config_path)
    wp_client = WordPressClient(
        settings.wp_base_url,
        settings.wp_username,
        settings.wp_application_password,
    )
    app = Application.builder().token(settings.telegram_bot_token).build()
    app.bot_data["settings"] = settings
    app.bot_data["wp_client"] = wp_client
    app.bot_data["catalogues"] = entries
    app.bot_data["catalogues_by_id"] = by_id(entries)

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("catalogues", cmd_catalogues))
    app.add_handler(CommandHandler("cancel", cmd_cancel))
    app.add_handler(CommandHandler("language", cmd_language))
    app.add_handler(CommandHandler("dil", cmd_language))
    app.add_handler(CallbackQueryHandler(on_language_pick, pattern=r"^lang:"))
    app.add_handler(CallbackQueryHandler(on_catalogue_pick, pattern=r"^c:"))
    app.add_handler(MessageHandler(filters.Document.ALL, on_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_plain_text))
    return app
