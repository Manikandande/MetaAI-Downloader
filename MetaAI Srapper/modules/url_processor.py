import yt_dlp
from modules.playwright_extractor import playwright_extract


def _yt_dlp_extract(url: str) -> dict:
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "format": "bestvideo+bestaudio/best",
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    formats = info.get("formats", [])
    video_url = info.get("url") or (formats[-1]["url"] if formats else None)
    if not video_url:
        raise ValueError("yt-dlp found no downloadable URL")

    return {
        "video_url": video_url,
        "title": info.get("title", "meta_ai_video"),
        "ext": info.get("ext", "mp4"),
        "filesize": info.get("filesize"),
        "source": "yt-dlp",
    }


def extract_video_info(url: str) -> dict:
    try:
        print(f"[url_processor] Trying yt-dlp for: {url}")
        result = _yt_dlp_extract(url)
        print(f"[url_processor] yt-dlp succeeded")
        return result
    except Exception as e:
        print(f"[url_processor] yt-dlp failed ({e}), falling back to Playwright")

    print(f"[url_processor] Launching Playwright...")
    result = playwright_extract(url)
    print(f"[url_processor] Playwright found: {result['video_url'][:80]}...")
    return result
