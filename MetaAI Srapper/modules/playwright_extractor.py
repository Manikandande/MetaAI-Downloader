import asyncio
import base64
import json
import re
import urllib.parse

VIDEO_URL_RE = re.compile(
    r'https?://[^\s\'"<>]+\.(?:mp4|webm|mov)(?:\?[^\s\'"<>]*)?',
    re.IGNORECASE
)

# Resolution keywords to score quality — higher score = better
_QUALITY_SCORES = [
    ("2160p", 2160), ("4k", 2160),
    ("1440p", 1440),
    ("1080p", 1080), ("fhd", 1080),
    ("720p", 720),  ("hd", 720),
    ("480p", 480),
    ("360p", 360),
    ("240p", 240),
]


def _quality_score(url: str) -> int:
    """Score a video URL by resolution. Handles plain URLs and Facebook CDN efg params."""
    # Try decoding Facebook CDN efg parameter (base64-encoded JSON with quality info)
    try:
        params = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        efg = params.get("efg", [None])[0]
        if efg:
            # Pad to a multiple of 4 before decoding
            padded = efg + "=" * (4 - len(efg) % 4)
            decoded = base64.b64decode(padded).decode("utf-8", errors="ignore")
            for keyword, score in _QUALITY_SCORES:
                if keyword in decoded.lower():
                    return score
    except Exception:
        pass

    # Fall back to plain text search in the URL
    lower = url.lower()
    for keyword, score in _QUALITY_SCORES:
        if keyword in lower:
            return score
    return 0


async def _extract_async(share_url: str) -> dict:
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()
        found_urls = []

        async def handle_response(response):
            url = response.url
            content_type = response.headers.get("content-type", "")
            if "video" in content_type:
                found_urls.append(url)
            elif any(ext in url.lower() for ext in [".mp4", ".webm", ".mov"]):
                found_urls.append(url)
            elif "json" in content_type or "javascript" in content_type:
                try:
                    body = await response.text()
                    matches = VIDEO_URL_RE.findall(body)
                    found_urls.extend(matches)
                except Exception:
                    pass

        page.on("response", handle_response)

        try:
            await page.goto(share_url, wait_until="networkidle", timeout=30000)
        except Exception:
            pass  # networkidle may time out on heavy SPAs; continue anyway

        # Wait longer to let higher-quality streams load
        await page.wait_for_timeout(5000)
        await browser.close()

    if not found_urls:
        raise RuntimeError(
            "No video URL found on this page. "
            "The link may require Meta login or may not contain a video."
        )

    # Deduplicate while preserving order
    seen = set()
    unique_urls = []
    for u in found_urls:
        if u not in seen:
            seen.add(u)
            unique_urls.append(u)

    # Pick the highest quality URL; fall back to first if none are scored
    best_url = max(unique_urls, key=_quality_score)
    best_score = _quality_score(best_url)

    print(f"[playwright] Found {len(unique_urls)} video URL(s). "
          f"Best quality: {best_score}p — {best_url[:80]}...")

    ext = "mp4"
    for candidate in [".webm", ".mov"]:
        if candidate in best_url.lower():
            ext = candidate.lstrip(".")
            break

    source = f"playwright ({best_score}p)" if best_score else "playwright"

    return {
        "video_url": best_url,
        "title": "meta_ai_video",
        "ext": ext,
        "filesize": None,
        "source": source,
    }


def playwright_extract(url: str) -> dict:
    return asyncio.run(_extract_async(url))
