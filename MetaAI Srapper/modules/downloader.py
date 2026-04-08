import re
import requests
from flask import Response, stream_with_context

CHUNK_SIZE = 1024 * 1024  # 1 MB


def _safe_filename(title: str, ext: str) -> str:
    safe = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_')
    safe = safe or "meta_ai_video"
    return f"{safe}.{ext}"


def stream_video(video_url: str, title: str, ext: str) -> Response:
    # Try HEAD to get content-length; some CDNs reject it — that's fine
    content_length = None
    content_type = f"video/{ext}"
    try:
        head = requests.head(video_url, allow_redirects=True, timeout=10)
        content_length = head.headers.get("Content-Length")
        content_type = head.headers.get("Content-Type", content_type)
    except Exception:
        pass

    def generate():
        with requests.get(video_url, stream=True, timeout=60) as r:
            r.raise_for_status()
            for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    yield chunk

    filename = _safe_filename(title, ext)
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Content-Type": content_type,
    }
    if content_length:
        headers["Content-Length"] = content_length

    return Response(
        stream_with_context(generate()),
        headers=headers,
        status=200,
    )
