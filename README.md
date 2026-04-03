# AlplerQuick — Telegram → catalog PDFs (WordPress HTML page)

Flow for authorized users:

1. **`/catalogues`** — pick which catalog row to update (inline buttons).
2. **Send a PDF** — the bot **linearizes** it (fast web view), uploads to the WordPress **Media Library**, then **replaces the matching `href`** inside the catalogues page content (Custom HTML / HTML block).

Catalog definitions (labels, which `href` to replace, upload filename) live in [`catalogues.json`](catalogues.json). Edit that file if URLs or titles change.

## WordPress setup

1. **REST API** — `/wp-json/` must work with Application Password auth.

2. **Application password** — User must be able to **upload media** and **edit** the catalogues page (`WP_PAGE_ID`).

3. **Page content** — The bot loads `GET /wp/v2/pages/{id}?context=edit` and patches `content` with the same string, only changing one `href="..."` that contains the configured **`href_marker`** (usually the PDF filename). If you change filenames in WordPress, update `href_marker` and `upload_filename` in `catalogues.json`.

4. **Find the page ID** — In the editor URL: `post=123` → `WP_PAGE_ID=123`.

## Telegram setup

1. Bot token from [@BotFather](https://t.me/BotFather).

2. Your numeric user ID in `ALLOWED_TELEGRAM_USER_IDS` (e.g. [@userinfobot](https://t.me/userinfobot)).

## Run locally

```bash
cd /path/to/AlplerQuick
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env
python main.py
```

**PDF linearization** uses [pikepdf](https://github.com/pikepdf/pikepdf) (QPDF). No separate `qpdf` binary is required.

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | BotFather token |
| `ALLOWED_TELEGRAM_USER_IDS` | Yes | Comma-separated Telegram user IDs |
| `WP_BASE_URL` | Yes | Site root, no trailing slash |
| `WP_USERNAME` | Yes | WP user |
| `WP_APPLICATION_PASSWORD` | Yes | Application password |
| `WP_PAGE_ID` | Yes | Catalogues page ID |
| `CATALOGUES_CONFIG` | No | Path to JSON (default `catalogues.json` in project root) |
| `BOT_MODE` | No | `polling` or `webhook` |
| `WEBHOOK_BASE_URL` | Webhook | Public `https://host` |
| `WEBHOOK_PATH` | No | Default `/telegram/webhook` |
| `PORT` | No | Webhook listen port (default `8080`) |
| `TELEGRAM_WEBHOOK_SECRET` | No | Optional BotFather secret |

## `catalogues.json`

Each entry:

- **`id`** — internal key for callbacks (ASCII, short).
- **`label`** — button text in Telegram.
- **`href_marker`** — unique substring of the current PDF URL in the page HTML (must match exactly once).
- **`upload_filename`** — filename used on upload (optional; defaults to marker if omitted).

After changing the live HTML in WordPress, adjust markers if filenames or paths change.

## Production webhook

Set `BOT_MODE=webhook`, `WEBHOOK_BASE_URL`, and `WEBHOOK_PATH` so `WEBHOOK_BASE_URL` + `WEBHOOK_PATH` is the full HTTPS URL Telegram calls. Proxy to `PORT`. Optional `TELEGRAM_WEBHOOK_SECRET`.

## Troubleshooting

- **“No href containing … found”** — Live page HTML no longer contains that substring; sync `catalogues.json` with the editor or REST `content.raw`.
- **“Multiple hrefs contain …”** — Use a longer, unique `href_marker`.
- **Linearize errors** — PDF may be encrypted or corrupted; try another export.
- **401 / 403** — Application password or capabilities; some hosts disable app passwords.

## Old ACF-based flow

This project no longer uses ACF. Updates target the **HTML block `href`** on the catalogues page only.
