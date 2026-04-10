import os
import tempfile
import yt_dlp
from modules.playwright_extractor import playwright_extract

# HD format preference: combined 1080p → 720p → any combined → merge if needed
_HD_FORMAT = (
    "best[height>=1080][ext=mp4]"
    "/best[height>=720][ext=mp4]"
    "/best[height>=1080]"
    "/best[height>=720]"
    "/bestvideo[height>=720][ext=mp4]+bestaudio[ext=m4a]"
    "/bestvideo[height>=720]+bestaudio"
    "/best"
)


def _yt_dlp_extract(url: str) -> dict:
    # Step 1: probe available formats without downloading
    probe_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "format": _HD_FORMAT,
    }
    with yt_dlp.YoutubeDL(probe_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    title = info.get("title", "meta_ai_video")
    requested_formats = info.get("requested_formats")  # set when format uses '+'

    # Step 2: if yt-dlp selected separate video+audio streams, we must merge
    if requested_formats and len(requested_formats) > 1:
        print("[url_processor] HD requires merging — downloading to temp file")
        tmpdir = tempfile.mkdtemp(prefix="metaai_")
        dl_opts = {
            "quiet": True,
            "no_warnings": True,
            "format": _HD_FORMAT,
            "outtmpl": os.path.join(tmpdir, "video.%(ext)s"),
            "merge_output_format": "mp4",
        }
        with yt_dlp.YoutubeDL(dl_opts) as ydl:
            ydl.extract_info(url, download=True)

        files = [f for f in os.listdir(tmpdir) if not f.endswith(".part")]
        if not files:
            raise ValueError("yt-dlp merge download produced no output file")

        filepath = os.path.join(tmpdir, files[0])
        ext = os.path.splitext(filepath)[1].lstrip(".") or "mp4"
        return {
            "local_file": filepath,
            "title": title,
            "ext": ext,
            "filesize": os.path.getsize(filepath),
            "source": "yt-dlp (HD merged)",
        }

    # Step 3: single combined stream — just return the direct URL
    formats = info.get("formats", [])
    video_url = info.get("url") or (formats[-1]["url"] if formats else None)
    if not video_url:
        raise ValueError("yt-dlp found no downloadable URL")

    height = info.get("height") or (formats[-1].get("height") if formats else None)
    source = f"yt-dlp ({height}p)" if height else "yt-dlp"
    return {
        "video_url": video_url,
        "title": title,
        "ext": info.get("ext", "mp4"),
        "filesize": info.get("filesize"),
        "source": source,
    }


def extract_video_info(url: str) -> dict:
    try:
        print(f"[url_processor] Trying yt-dlp for: {url}")
        result = _yt_dlp_extract(url)
        print(f"[url_processor] yt-dlp succeeded ({result.get('source')})")
        return result
    except Exception as e:
        print(f"[url_processor] yt-dlp failed ({e}), falling back to Playwright")

    print("[url_processor] Launching Playwright...")
    result = playwright_extract(url)
    video_url = result.get("video_url", "")
    print(f"[url_processor] Playwright found: {video_url[:80]}...")
    return result
