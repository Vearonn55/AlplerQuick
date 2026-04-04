# AlplerQuick — Telegram → catalog PDFs (WordPress HTML page)

Flow for authorized users:

1. **`/catalogues`** — pick which catalog row to update (inline buttons).
2. **Send a PDF** — the bot **linearizes** it (fast web view), uploads to the WordPress **Media Library**, then **replaces the matching `href`** inside the catalogues page content (Custom HTML / HTML block).

Catalog definitions (labels, which `href` to replace, upload filename) live in [`catalogues.json`](catalogues.json). Edit that file if URLs or titles change.

## WordPress setup

1. **REST API** — `/wp-json/` must work with Application Password auth. The bot calls `https://YOUR-SITE/wp-json/wp/v2/...` (if media upload returns **404**, an old build may have used the wrong path; redeploy, or test with `curl -I "https://YOUR-SITE/wp-json/wp/v2/types"`).

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

## Deploy on VPS with Docker (polling)

**Polling** means the container calls Telegram over **outbound HTTPS** only. You do **not** open a port or change nginx for the bot. (`kurulum.alplerltd.com` can stay as your InstallOps site only.)

### 1. Install Docker on the server

Ubuntu example — use **Compose V2** (`docker compose` with a **space**). The old `docker-compose` 1.x from apt often breaks on newer Docker with `KeyError: 'ContainerConfig'`.

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-v2
sudo systemctl enable --now docker
docker compose version   # must work; use this, not docker-compose
```

If you still have the legacy `docker-compose` command and hit `ContainerConfig` errors, remove it and use only V2:

```bash
sudo apt remove -y docker-compose   # optional: drops python docker-compose 1.29.x
```

Add your SSH user to the `docker` group if you avoid `sudo` (then log out and back in):

```bash
sudo usermod -aG docker $USER
```

### 2. Put the project on the server

```bash
sudo mkdir -p /opt/AlplerQuick
sudo chown $USER:$USER /opt/AlplerQuick
cd /opt/AlplerQuick
git clone <your-repo-url> .
# next time: cd /opt/AlplerQuick && git pull
```

### 3. Create `.env` (only variables, never nginx)

```bash
cp .env.example .env
nano .env
```

Fill at least:

| Variable | Example / note |
|----------|----------------|
| `TELEGRAM_BOT_TOKEN` | From [@BotFather](https://t.me/BotFather) |
| `ALLOWED_TELEGRAM_USER_IDS` | Your numeric ID(s), comma-separated |
| `WP_BASE_URL` | `https://www.alplerltd.com` (no trailing slash) |
| `WP_USERNAME` | WordPress user |
| `WP_APPLICATION_PASSWORD` | Application password (spaces optional) |
| `WP_PAGE_ID` | Catalogues page ID |
| `BOT_MODE` | `polling` |

Leave **webhook** variables commented out. **Do not** paste nginx `server {` blocks into `.env` — nginx belongs under `/etc/nginx/sites-available/`.

### 4. Build and start the container

Ensure `docker-compose.yml` has **no** `ports:` section uncommented (default for polling).

```bash
cd /opt/AlplerQuick
docker compose build
docker compose up -d
docker compose logs -f
```

Stop following logs with `Ctrl+C`; the container keeps running.

### 5. Verify

- In Telegram, open your bot and send `/start`, then `/catalogues`, pick a row, send a test PDF (or skip PDF on production until ready).
- If something fails, check: `docker compose logs --tail=100 alplerquick`

### 6. After you change code or `catalogues.json`

```bash
cd /opt/AlplerQuick
git pull
docker compose up -d --build
# If you only edited catalogues.json on disk:
docker compose restart alplerquick
```

### Optional: webhook later

If you switch to webhook, set `BOT_MODE=webhook` and webhook env vars, uncomment `ports` in `docker-compose.yml`, add [`deploy/installops-telegram-webhook.fragment.conf`](deploy/installops-telegram-webhook.fragment.conf) to nginx, then `sudo nginx -t && sudo systemctl reload nginx`.

## Troubleshooting

- **`KeyError: 'ContainerConfig'`** (during `docker-compose up`) — Your **`docker-compose` is version 1.x** and is incompatible with the current Docker Engine. Use **Compose V2**: `sudo apt install docker-compose-v2`, then always run **`docker compose`** (space, not hyphen). Clean up: `docker rm -f alplerquick 2>/dev/null; docker compose -f /opt/AlplerQuick/docker-compose.yml down` then `docker compose up -d --build` from the project directory.
- **`BOT_MODE must be polling or webhook`** — Often **`BOT_MODE=pooling`** (wrong spelling). Use **`polling`** with two **l**’s. Also fix empty `BOT_MODE=` or stray quotes (`BOT_MODE="polling"` is OK; the app strips them).
- **“.env” contains `server {` or `location`”** — That is nginx config; move it to `/etc/nginx/sites-available/installops-frontend.conf` (or your site file). Restore `.env` from `.env.example` and re-enter secrets.
- **“No href containing … found”** — Live page HTML no longer contains that substring; sync `catalogues.json` with the editor or REST `content.raw`.
- **“Multiple hrefs contain …”** — Use a longer, unique `href_marker`.
- **Linearize errors** — PDF may be encrypted or corrupted; try another export.
- **401 / 403** — Application password or capabilities; some hosts disable app passwords.
- **`rest_cannot_create` on media upload** — Not a Python bug: the WordPress user tied to the Application Password lacks **`upload_files`**. In **Kullanıcılar** set that account’s role to **Yazar** (Author) or **Editör** (Editor) / **Yönetici** (Admin), then create a **new** application password and update `.env`.
- **Media upload 404** — (1) **Rebuild without cache** so the image includes `/wp-json/` in API URLs: `docker compose build --no-cache && docker compose up -d`. Verify: `docker compose exec alplerquick grep -n wp-json /app/src/wp_client.py` (should show `self._rest = .../wp-json/wp/v2`). (2) Wrong `WP_BASE_URL` (subdirectory install). (3) Security plugin/WAF returning fake 404 for REST uploads — test in browser or `curl -X POST` with Application Password.

## Old ACF-based flow

This project no longer uses ACF. Updates target the **HTML block `href`** on the catalogues page only.
