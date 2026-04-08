import asyncio
import re

VIDEO_URL_RE = re.compile(
    r'https?://[^\s\'"<>]+\.(?:mp4|webm|mov)(?:\?[^\s\'"<>]*)?',
    re.IGNORECASE
)


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

        await page.wait_for_timeout(3000)
        await browser.close()

    if not found_urls:
        raise RuntimeError(
            "No video URL found on this page. "
            "The link may require Meta login or may not contain a video."
        )

    video_url = found_urls[0]
    ext = "mp4"
    for candidate in [".webm", ".mov"]:
        if candidate in video_url.lower():
            ext = candidate.lstrip(".")
            break

    return {
        "video_url": video_url,
        "title": "meta_ai_video",
        "ext": ext,
        "filesize": None,
        "source": "playwright",
    }


def playwright_extract(url: str) -> dict:
    return asyncio.run(_extract_async(url))
