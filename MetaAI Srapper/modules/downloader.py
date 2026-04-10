import os
import re
import requests
from flask import Response, stream_with_context

CHUNK_SIZE = 1024 * 1024  # 1 MB


def _safe_filename(title: str, ext: str) -> str:
    safe = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_')
    safe = safe or "meta_ai_video"
    return f"{safe}.{ext}"


def stream_local_file(filepath: str, title: str, ext: str) -> Response:
    """Stream a locally downloaded file and delete it afterwards."""
    filename = _safe_filename(title, ext)
    filesize = os.path.getsize(filepath)

    def generate():
        try:
            with open(filepath, "rb") as f:
                while True:
                    chunk = f.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    yield chunk
        finally:
            # Clean up temp file and its parent temp directory
            try:
                os.remove(filepath)
                tmpdir = os.path.dirname(filepath)
                if tmpdir.startswith(os.path.join(os.path.sep, "tmp")) or \
                   "metaai_" in os.path.basename(tmpdir):
                    os.rmdir(tmpdir)
            except Exception:
                pass

    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Content-Type": f"video/{ext}",
        "Content-Length": str(filesize),
    }
    return Response(stream_with_context(generate()), headers=headers, status=200)


def stream_video(video_url: str, title: str, ext: str) -> Response:
    """Stream video directly from a remote URL."""
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

    return Response(stream_with_context(generate()), headers=headers, status=200)
