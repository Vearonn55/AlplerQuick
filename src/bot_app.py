"""Telegram: pick catalogue → send PDF → linearize → WP media + HTML href update."""

from __future__ import annotations

import asyncio
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

from src.catalogues import CatalogueEntry, by_id, load_catalogues
from src.config import Settings
from src.html_replace import HrefReplaceError, replace_href_by_selector
from src.pdf_linearize import LinearizeError, linearize_pdf_bytes
from src.wp_client import WordPressClient, WordPressError

logger = logging.getLogger(__name__)

PDF_MIME = "application/pdf"
CALLBACK_PREFIX = "c:"
USER_DATA_CATALOG = "pending_catalog_id"


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


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Use /catalogues to choose which catalog PDF to replace on the website. "
        "Then send a PDF file; it will be linearized, uploaded to WordPress, and the "
        "catalog page link will point to the new file.\n\n/cancel clears your selection."
    )


async def cmd_catalogues(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.bot_data["settings"]
    if not _authorized(update.effective_user.id if update.effective_user else None, settings):
        await update.message.reply_text("You are not authorized.")
        return
    entries: list[CatalogueEntry] = context.bot_data["catalogues"]
    await update.message.reply_text(
        "Which catalogue should the next PDF replace?",
        reply_markup=_catalogue_keyboard(entries),
    )


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.bot_data["settings"]
    if not _authorized(update.effective_user.id if update.effective_user else None, settings):
        await update.message.reply_text("You are not authorized.")
        return
    context.user_data.pop(USER_DATA_CATALOG, None)
    await update.message.reply_text("Selection cleared. Use /catalogues to pick again.")


async def on_catalogue_pick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return
    await query.answer()
    settings: Settings = context.bot_data["settings"]
    if not _authorized(query.from_user.id if query.from_user else None, settings):
        await query.edit_message_text("You are not authorized.")
        return
    data = query.data or ""
    if not data.startswith(CALLBACK_PREFIX):
        return
    cat_id = data[len(CALLBACK_PREFIX) :]
    cmap: dict[str, CatalogueEntry] = context.bot_data["catalogues_by_id"]
    entry = cmap.get(cat_id)
    if not entry:
        await query.edit_message_text("Unknown catalogue.")
        return
    context.user_data[USER_DATA_CATALOG] = cat_id
    await query.edit_message_text(
        f"Selected: {entry.label}\n\n"
        "Send the PDF as a document. It will be linearized and the catalog link on the page will be updated.\n\n"
        "/cancel to clear this selection."
    )


async def on_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.bot_data["settings"]
    wp: WordPressClient = context.bot_data["wp_client"]
    cmap: dict[str, CatalogueEntry] = context.bot_data["catalogues_by_id"]

    user = update.effective_user
    if not _authorized(user.id if user else None, settings):
        logger.info("Rejected document from unauthorized user id=%s", user.id if user else None)
        await update.message.reply_text("You are not authorized to upload.")
        return

    cat_id = context.user_data.get(USER_DATA_CATALOG)
    if not cat_id:
        await update.message.reply_text("First choose a catalogue with /catalogues, then send the PDF.")
        return

    entry = cmap.get(cat_id)
    if not entry:
        context.user_data.pop(USER_DATA_CATALOG, None)
        await update.message.reply_text("Invalid selection. Use /catalogues again.")
        return

    if not _is_pdf_document(update):
        await update.message.reply_text("Please send a PDF file (document).")
        return

    doc = update.message.document
    await update.message.reply_text("Downloading…")

    try:
        tg_file = await context.bot.get_file(doc.file_id)
        data = await tg_file.download_as_bytearray()
        file_bytes = bytes(data)
    except Exception as exc:
        logger.exception("Telegram download failed")
        await update.message.reply_text(f"Could not download file from Telegram: {exc}")
        return

    await update.message.reply_text("Linearizing PDF…")
    try:
        linearized = await asyncio.to_thread(linearize_pdf_bytes, file_bytes)
    except LinearizeError as exc:
        await update.message.reply_text(f"Could not linearize PDF: {exc}")
        return

    filename = entry.upload_filename
    if not filename.lower().endswith(".pdf"):
        filename = f"{filename}.pdf"

    await update.message.reply_text("Uploading to WordPress and updating the catalog page…")
    try:
        media = await wp.upload_media(linearized, filename)
        source_url = media.get("source_url") or media.get("link") or ""
        if not source_url:
            raise WordPressError("Upload succeeded but no source_url in response")

        raw = await wp.get_page_raw_content(settings.wp_page_id)
        updated = replace_href_by_selector(raw, entry.selector, source_url)
        await wp.patch_page_raw_content(settings.wp_page_id, updated)
    except (WordPressError, HrefReplaceError) as exc:
        await update.message.reply_text(f"WordPress/HTML error: {exc}")
        return
    except Exception as exc:
        logger.exception("Unexpected error during WordPress update")
        await update.message.reply_text(f"Unexpected error: {exc}")
        return

    context.user_data.pop(USER_DATA_CATALOG, None)
    msg = f"Done. {entry.label} now points to:\n{source_url}"
    await update.message.reply_text(msg)


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
    app.add_handler(CallbackQueryHandler(on_catalogue_pick, pattern=r"^c:"))
    app.add_handler(MessageHandler(filters.Document.ALL, on_document))
    return app
