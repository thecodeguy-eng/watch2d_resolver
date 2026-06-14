"""
Watch2D — standalone download-link resolver.

A tiny, independent copy of the website's `resolve_download_link` view, so the
mobile app can resolve real (token-gated) download links even when the main
Watch2D site is slow or down.

Contract (identical to the website):
    GET /resolve-download/?url=<landing_url>
    ->  {"download_url": "<direct or fallback url>"}

Run locally:
    pip install -r requirements.txt
    uvicorn app:app --host 0.0.0.0 --port 8000
"""
import re
from urllib.parse import urlparse, urlunparse

import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI(title="Watch2D Resolver", version="1.0.0")

# The app (and Flutter web) call this cross-origin, so allow any origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

DIRECT_EXTS = (".mp4", ".mkv", ".webm", ".avi", ".mov", ".zip", ".rar")


# ── scraper helpers ──────────────────────────────────────────────────────────
def _get_scraper():
    try:
        import cloudscraper
        return cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "mobile": False}
        )
    except Exception:
        session = requests.Session()
        session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        })
        return session


def _fetch_html_safe(url):
    try:
        scraper = _get_scraper()
        resp = scraper.get(url, timeout=15, allow_redirects=True)
        return resp.text, None
    except Exception as e1:
        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
            resp = requests.get(url, headers=headers, timeout=12, allow_redirects=True)
            return resp.text, None
        except Exception as e2:
            return None, f"cloudscraper: {e1} | requests: {e2}"


# ── host-specific resolvers ──────────────────────────────────────────────────
def _resolve_downloadwella(landing_url, parsed):
    try:
        path_parts = [p for p in parsed.path.split("/") if p]
        if not path_parts:
            return None
        file_code = path_parts[0]

        scraper = _get_scraper()
        base = f"{parsed.scheme}://{parsed.netloc}"
        scraper.get(landing_url, timeout=12)

        post_data = {
            "op": "download2", "id": file_code, "rand": "",
            "referer": "", "method_free": "", "method_premium": "",
        }
        resp = scraper.post(base + "/", data=post_data, timeout=15,
                            headers={"Referer": landing_url})
        html = resp.text

        m = re.search(
            r"location\.href\s*=\s*[\x27\x22]"
            r"(https?://[^\x27\x22]+\.(?:mp4|mkv|webm|avi|zip|rar)[^\x27\x22]*)[\x27\x22]",
            html, re.IGNORECASE)
        if m:
            return m.group(1)

        m = re.search(r"location\.href\s*=\s*[\x27\x22]"
                      r"(https?://[^\x27\x22]{30,})[\x27\x22]", html)
        if m:
            url = m.group(1)
            if any(x in url.lower() for x in ["/dl/", "kissorgrab", "cdn"]):
                return url

        m = re.search(
            r'href=["|\x27]((https?://)[^"|\x27?\s]{10,}\.(?:mp4|mkv|webm|avi|zip|rar))["|\x27]',
            html, re.IGNORECASE)
        if m:
            return m.group(1)
        return None
    except Exception:
        return None


def _resolve_loadedfiles(landing_url, parsed):
    """loadedfiles.org checks Referer AND a session cookie; warm up first."""
    dbg = {}
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        session = requests.Session()
        session.headers.update(HEADERS)

        home_url = f"{parsed.scheme}://{parsed.netloc}/"
        try:
            session.get(home_url, timeout=10, allow_redirects=True)
        except Exception:
            pass  # non-fatal

        resp = session.get(landing_url, timeout=15, allow_redirects=True,
                           headers={"Referer": "https://9jarocks.net/"})
        if resp.status_code != 200:
            return None
        html = resp.text

        m = re.search(
            r"var\s+downloadUrl\s*=\s*['\"]"
            r"(https?://[^'\"]+\?pt=[^'\"]+)['\"]", html, re.IGNORECASE)
        if m:
            return m.group(1).strip()

        m = re.search(
            r"window\.location(?:\.href)?\s*=\s*['\"]"
            r"(https?://[^'\"]+\?pt=[^'\"]+)['\"]", html, re.IGNORECASE)
        if m:
            return m.group(1).strip()

        m = re.search(
            r"['\"](https?://loadedfiles\.org/[^'\"]+\?pt=[^'\"]+)['\"]",
            html, re.IGNORECASE)
        if m:
            return m.group(1).strip()
        return None
    except Exception:
        return None


def _extract_download_url(html, host):
    m = re.search(
        r"\.html\(['\"].*?href=[\\'\"]+((https?://)[^\'\"\\ ]+\?pt=[^\'\"\\ ]+)[\\'\"]\",",
        html, re.DOTALL)
    if m:
        return m.group(1)

    m = re.search(r"href=['\"](https?://[^'\">\s]+\?pt=[^'\">\s]+)['\"]", html)
    if m:
        return m.group(1)

    m = re.search(r"[\x27\x22]((https?://)[^\x27\x22]{5,}\?pt=[^\x27\x22]{10,})[\x27\x22]", html)
    if m:
        return m.group(1)

    m = re.search(r"location\.href\s*=\s*['\"](https?://[^'\"]{20,})['\"]", html)
    if m:
        url = m.group(1)
        if any(x in url.lower() for x in ["/dl/", "kissorgrab", ".mkv", ".mp4", ".avi", ".zip"]):
            return url

    m = re.search(
        r"window\.location(?:\.href)?\s*=\s*['\"]"
        r"(https?://[^'\"]+\.(?:mp4|mkv|webm|avi|zip|rar)[^'\"]*)['\"]\",",
        html, re.IGNORECASE)
    if m:
        return m.group(1)

    m = re.search(
        r"[\x27\x22](https?://[^\x27\x22?\s]{10,}\.(?:mp4|mkv|webm|avi|zip|rar))[\x27\x22]",
        html, re.IGNORECASE)
    if m:
        return m.group(1)

    return None


# ── main endpoint (same contract as the website) ─────────────────────────────
def _resolve(landing_url: str) -> str:
    parsed = urlparse(landing_url)
    host = parsed.netloc.lower()
    lower = landing_url.lower()

    # sabishares preview → strip query
    if "sabishares.com" in host and "preview" in parsed.query:
        return urlunparse(parsed._replace(query="", fragment=""))

    # already direct
    if "?pt=" in lower or any(lower.endswith(ext) for ext in DIRECT_EXTS):
        return landing_url

    # passthrough hosts
    if "mylulutv.com" in host:
        return landing_url

    if "downloadwella.com" in host:
        return _resolve_downloadwella(landing_url, parsed) or landing_url

    if "loadedfiles.org" in host:
        return _resolve_loadedfiles(landing_url, parsed) or landing_url

    # generic HTML fetch + extract
    html, _ = _fetch_html_safe(landing_url)
    if not html:
        return landing_url
    return _extract_download_url(html, host) or landing_url


@app.get("/resolve-download/")
def resolve_download(url: str = ""):
    url = (url or "").strip()
    if not url:
        return JSONResponse({"error": "No URL provided"}, status_code=400)
    try:
        return {"download_url": _resolve(url)}
    except Exception:
        # Never fail the app — fall back to the original link.
        return {"download_url": url}


@app.get("/")
def health():
    return {"status": "ok", "service": "watch2d-resolver"}
