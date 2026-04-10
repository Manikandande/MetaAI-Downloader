import uuid
from flask import Flask, request, jsonify, Response
from modules.url_processor import extract_video_info
from modules.downloader import stream_video, stream_local_file

app = Flask(__name__, static_folder="static", static_url_path="")

# Temporary store for locally downloaded/merged files: {key: {local_file, title, ext}}
_pending_downloads: dict = {}


@app.route("/")
def index():
    return app.send_static_file("index.html")


@app.route("/api/info", methods=["POST"])
def get_info():
    data = request.get_json()
    url = (data or {}).get("url", "").strip()
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    try:
        info = extract_video_info(url)

        # If yt-dlp merged streams into a local file, register it with a key
        if "local_file" in info:
            key = str(uuid.uuid4())
            _pending_downloads[key] = {
                "local_file": info["local_file"],
                "title": info["title"],
                "ext": info["ext"],
            }
            return jsonify({
                "download_key": key,
                "title": info["title"],
                "ext": info["ext"],
                "filesize": info["filesize"],
                "source": info["source"],
            })

        return jsonify(info)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/download", methods=["GET", "POST"])
def download():
    if request.method == "GET":
        download_key = request.args.get("download_key", "").strip()
        video_url   = request.args.get("video_url", "").strip()
        title       = request.args.get("title", "meta_ai_video")
        ext         = request.args.get("ext", "mp4")
        instagram   = request.args.get("instagram", "false").lower() == "true"
    else:
        data = request.get_json() or {}
        download_key = data.get("download_key", "").strip()
        video_url   = data.get("video_url", "").strip()
        title       = data.get("title", "meta_ai_video")
        ext         = data.get("ext", "mp4")
        instagram   = str(data.get("instagram", "false")).lower() == "true"

    try:
        # Resolve local file (from yt-dlp merge)
        local_file = None
        if download_key:
            entry = _pending_downloads.pop(download_key, None)
            if not entry:
                return jsonify({"error": "Download key not found or already used"}), 404
            local_file = entry["local_file"]
            title = entry["title"]
            ext = entry["ext"]

        # Upscale to 1080p for Instagram if requested
        if instagram:
            from modules.upscaler import upscale_to_1080p, upscale_from_url
            print(f"[app] Upscaling to 1080p for Instagram...")
            if local_file:
                upscaled = upscale_to_1080p(local_file)
            else:
                upscaled = upscale_from_url(video_url)
            print(f"[app] Upscale done: {upscaled}")
            return stream_local_file(upscaled, title, "mp4")

        # Normal download
        if local_file:
            return stream_local_file(local_file, title, ext)

        if not video_url:
            return jsonify({"error": "No video_url or download_key provided"}), 400
        return stream_video(video_url, title, ext)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8085, debug=True)  # 0.0.0.0 allows mobile on same Wi-Fi
