import os
import subprocess
import tempfile

FFMPEG = "/opt/homebrew/bin/ffmpeg"


def upscale_to_1080p(input_path: str) -> str:
    """Upscale video to 1080p using ffmpeg. Returns path to output file."""
    tmpdir = tempfile.mkdtemp(prefix="metaai_ig_")
    output_path = os.path.join(tmpdir, "instagram_1080p.mp4")

    cmd = [
        FFMPEG, "-y", "-i", input_path,
        "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,"
               "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black",
        "-c:v", "libx264", "-crf", "18", "-preset", "fast",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg upscale failed: {result.stderr[-300:]}")

    return output_path


def upscale_from_url(video_url: str) -> str:
    """Download a remote video to a temp file, then upscale to 1080p."""
    import requests

    tmpdir = tempfile.mkdtemp(prefix="metaai_dl_")
    input_path = os.path.join(tmpdir, "source.mp4")

    with requests.get(video_url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(input_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

    output_path = upscale_to_1080p(input_path)

    # Clean up the source temp file
    try:
        os.remove(input_path)
        os.rmdir(tmpdir)
    except Exception:
        pass

    return output_path
