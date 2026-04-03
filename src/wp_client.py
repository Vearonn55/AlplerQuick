"""WordPress REST API: media upload and page content (HTML block) update."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

class WordPressError(Exception):
    """Raised when WordPress returns an error response."""

    def __init__(self, message: str, status_code: int | None = None, body: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class WordPressClient:
    def __init__(
        self,
        base_url: str,
        username: str,
        application_password: str,
        timeout: float = 120.0,
    ):
        self._base = base_url.rstrip("/")
        self._auth = (username, application_password)
        self._timeout = timeout
        # REST routes live under /wp-json/wp/v2/ (not /wp/v2/ — that 404s)
        self._rest = f"{self._base}/wp-json/wp/v2"
        self._headers = {
            "User-Agent": f"Mozilla/5.0 (compatible; AlplerQuick/1.0; +{self._base})",
        }

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=self._timeout,
            follow_redirects=True,
            headers=self._headers,
        )

    async def upload_media(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str = "application/pdf",
    ) -> dict[str, Any]:
        url = f"{self._rest}/media"
        files = {"file": (filename, file_bytes, content_type)}
        async with self._client() as client:
            response = await client.post(url, auth=self._auth, files=files)
        if response.status_code not in (200, 201):
            logger.warning(
                "WP media upload failed: url=%s final_url=%s status=%s body=%s",
                url,
                str(response.url),
                response.status_code,
                response.text[:800],
            )
            hint = ""
            if response.status_code == 404 and "/wp-json/" not in str(response.url):
                hint = " (URL missing /wp-json/? Rebuild image: docker compose build --no-cache.)"
            elif response.status_code == 404:
                hint = " (404 often = security plugin blocking REST, or wrong site URL.)"
            detail = (response.text or "")[:400].replace("\n", " ")
            raise WordPressError(
                f"Media upload failed ({response.status_code}){hint}" + (f" — {detail}" if detail else ""),
                status_code=response.status_code,
                body=response.text,
            )
        return response.json()

    async def get_page_raw_content(self, page_id: int) -> str:
        url = f"{self._rest}/pages/{page_id}"
        async with self._client() as client:
            response = await client.get(url, auth=self._auth, params={"context": "edit"})
        if response.status_code != 200:
            logger.warning("WP get page failed: %s %s", response.status_code, response.text)
            raise WordPressError(
                f"Could not load page ({response.status_code})",
                status_code=response.status_code,
                body=response.text,
            )
        data = response.json()
        content = data.get("content")
        if isinstance(content, dict):
            raw = content.get("raw")
        else:
            raw = content if isinstance(content, str) else None
        if raw is None:
            raw = ""
        return str(raw)

    async def patch_page_raw_content(self, page_id: int, raw_content: str) -> dict[str, Any]:
        url = f"{self._rest}/pages/{page_id}"
        payload = {"content": raw_content}
        async with self._client() as client:
            response = await client.patch(
                url,
                auth=self._auth,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
        if response.status_code not in (200, 201):
            logger.warning("WP page patch failed: %s %s", response.status_code, response.text)
            raise WordPressError(
                f"Page update failed ({response.status_code})",
                status_code=response.status_code,
                body=response.text,
            )
        return response.json()
