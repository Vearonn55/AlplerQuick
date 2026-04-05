"""User-facing bot strings: English and Turkish."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from telegram.ext import ContextTypes

USER_DATA_LOCALE = "locale_override"  # "en" | "tr" | None → auto from Telegram

MESSAGES: dict[str, dict[str, str]] = {
    "en": {
        "start": (
            "Welcome. Use this bot to replace catalog PDFs on the website.\n\n"
            "Steps:\n"
            "1. /catalogues — pick which catalog row to update\n"
            "2. Send the PDF as a document (not a photo)\n\n"
            "Important: Telegram only lets bots download files up to 20 MB. "
            "If your PDF is larger, compress or split it before sending.\n\n"
            "/start — show this help again\n"
            "/cancel — clear your catalog selection\n"
            "/language — choose English or Turkish (or /dil)"
        ),
        "not_authorized": "You are not authorized. Use /start to see what this bot does.",
        "not_authorized_upload": (
            "You are not authorized to upload. Use /start to see what this bot does."
        ),
        "catalogues_prompt": (
            "Which catalogue should the next PDF replace?\n\n"
            "Reminder: PDFs must be 20 MB or smaller for the bot to download them. /start for full help."
        ),
        "cancel_cleared": (
            "Selection cleared. Use /catalogues to pick again, or /start for help."
        ),
        "callback_not_authorized": "You are not authorized.",
        "unknown_catalogue": "Unknown catalogue.",
        "selected_catalog": (
            "Selected: {label}\n\n"
            "Send the PDF as a document (max 20 MB). It will be linearized and the catalog link on the page will be updated.\n\n"
            "/cancel to clear this selection. /start for help."
        ),
        "document_no_catalog": (
            "Use /start for instructions. Then run /catalogues, pick a row, and send a PDF (max 20 MB)."
        ),
        "invalid_selection": "Invalid selection. Use /catalogues again, or /start for help.",
        "send_pdf_document": "Please send a PDF file (document). Use /start for the full steps.",
        "file_too_large": (
            "This file is about {size_mb:.1f} MB. Telegram only allows bots to download files up to 20 MB. "
            "Compress or split the PDF and try again. Use /start for details."
        ),
        "downloading": "Downloading…",
        "download_failed_suffix": (
            "\n\nLikely over the 20 MB bot download limit. Compress the PDF or send a smaller file. "
            "Use /start for help."
        ),
        "linearizing": "Linearizing PDF…",
        "linearize_failed": "Could not linearize PDF: {error}",
        "uploading_wp": "Uploading to WordPress and updating the catalog page…",
        "wp_html_error": "WordPress/HTML error: {error}",
        "unexpected_error": "Unexpected error: {error}",
        "done": "Done. {label} now points to:\n{url}",
        "plain_text_nudge": (
            "This bot only accepts PDF documents after you pick a catalogue. "
            "Use /start for step-by-step help and the 20 MB file limit, then /catalogues."
        ),
        "language_current_auto": (
            "Language follows your Telegram app (currently: {lang}).\n"
            "Override: /language en or /language tr — reset with /language auto"
        ),
        "language_current_fixed": "Bot language is set to: {lang}.\nReset with /language auto",
        "language_set_en": "Language set to English.",
        "language_set_tr": "Language set to Turkish.",
        "language_auto": "Language will follow your Telegram app settings again.",
        "language_help": (
            "Usage: /language en — English\n"
            "/language tr — Turkish\n"
            "/language auto — use Telegram app language\n"
            "Alias: /dil"
        ),
        "lang_en": "English",
        "lang_tr": "Turkish",
    },
    "tr": {
        "start": (
            "Hoş geldiniz. Bu bot, web sitesindeki katalog PDF'lerini güncellemek içindir.\n\n"
            "Adımlar:\n"
            "1. /catalogues — güncellenecek katalog satırını seçin\n"
            "2. PDF'yi belge olarak gönderin (fotoğraf değil)\n\n"
            "Önemli: Telegram, botların yalnızca 20 MB'a kadar dosya indirmesine izin verir. "
            "PDF daha büyükse göndermeden önce sıkıştırın veya bölün.\n\n"
            "/start — bu yardımı tekrar gösterir\n"
            "/cancel — katalog seçimini temizler\n"
            "/language veya /dil — dil seçimi (İngilizce/Türkçe)"
        ),
        "not_authorized": "Yetkiniz yok. Botun ne yaptığını görmek için /start kullanın.",
        "not_authorized_upload": (
            "Yükleme yapmanıza izin verilmiyor. Botun ne yaptığını görmek için /start kullanın."
        ),
        "catalogues_prompt": (
            "Hangi katalog satırı güncellensin?\n\n"
            "Hatırlatma: Botun indirebilmesi için PDF'ler en fazla 20 MB olmalıdır. Tüm yardım için /start."
        ),
        "cancel_cleared": (
            "Seçim temizlendi. Tekrar seçmek için /catalogues kullanın veya yardım için /start."
        ),
        "callback_not_authorized": "Yetkiniz yok.",
        "unknown_catalogue": "Bilinmeyen katalog.",
        "selected_catalog": (
            "Seçildi: {label}\n\n"
            "PDF'yi belge olarak gönderin (en fazla 20 MB). Dosya doğrusallaştırılacak ve sayfadaki katalog bağlantısı güncellenecek.\n\n"
            "Seçimi temizlemek için /cancel. Yardım için /start."
        ),
        "document_no_catalog": (
            "Yardım için /start kullanın. Ardından /catalogues çalıştırın, bir satır seçin ve PDF gönderin (en fazla 20 MB)."
        ),
        "invalid_selection": "Geçersiz seçim. Tekrar /catalogues kullanın veya yardım için /start.",
        "send_pdf_document": "Lütfen PDF dosyasını belge olarak gönderin. Tüm adımlar için /start.",
        "file_too_large": (
            "Bu dosya yaklaşık {size_mb:.1f} MB. Telegram, botların yalnızca 20 MB'a kadar dosya indirmesine izin verir. "
            "PDF'yi sıkıştırın veya bölün ve tekrar deneyin. Ayrıntılar için /start."
        ),
        "downloading": "İndiriliyor…",
        "download_failed_suffix": (
            "\n\nMuhtemelen 20 MB bot indirme sınırı aşıldı. PDF'yi sıkıştırın veya daha küçük bir dosya gönderin. "
            "Yardım için /start."
        ),
        "linearizing": "PDF doğrusallaştırılıyor…",
        "linearize_failed": "PDF doğrusallaştırılamadı: {error}",
        "uploading_wp": "WordPress'e yükleniyor ve katalog sayfası güncelleniyor…",
        "wp_html_error": "WordPress/HTML hatası: {error}",
        "unexpected_error": "Beklenmeyen hata: {error}",
        "done": "Tamam. {label} artık şuraya bağlanıyor:\n{url}",
        "plain_text_nudge": (
            "Bu bot yalnızca katalog seçtikten sonra PDF belgelerini kabul eder. "
            "Adım adım yardım ve 20 MB dosya sınırı için /start, ardından /catalogues kullanın."
        ),
        "language_current_auto": (
            "Dil, Telegram uygulamanıza göre ayarlanıyor (şu an: {lang}).\n"
            "Zorla: /language en veya /language tr — sıfırlamak için /language auto"
        ),
        "language_current_fixed": "Bot dili: {lang}.\nSıfırlamak için /language auto",
        "language_set_en": "Dil İngilizce olarak ayarlandı.",
        "language_set_tr": "Dil Türkçe olarak ayarlandı.",
        "language_auto": "Dil tekrar Telegram uygulama ayarlarınıza göre belirlenecek.",
        "language_help": (
            "Kullanım: /language en — İngilizce\n"
            "/language tr — Türkçe\n"
            "/language auto — Telegram diline dön\n"
            "Kısayol: /dil"
        ),
        "lang_en": "İngilizce",
        "lang_tr": "Türkçe",
    },
}


def _telegram_language_code(user) -> str | None:
    if user is None:
        return None
    lc = getattr(user, "language_code", None)
    if not lc or not isinstance(lc, str):
        return None
    return lc.strip().lower() or None


def locale_from_telegram(user) -> str:
    """Pick locale from Telegram profile (no user_data override)."""
    lc = _telegram_language_code(user)
    if lc and (lc == "tr" or lc.startswith("tr-")):
        return "tr"
    return "en"


def effective_locale(context: "ContextTypes.DEFAULT_TYPE", user) -> str:
    override = context.user_data.get(USER_DATA_LOCALE)
    if override in MESSAGES:
        return override
    return locale_from_telegram(user)


def t(locale: str, key: str, **kwargs: object) -> str:
    lang = locale if locale in MESSAGES else "en"
    template = MESSAGES[lang].get(key) or MESSAGES["en"][key]
    return template.format(**kwargs)
