from flask import Flask, request, jsonify, Response
from modules.url_processor import extract_video_info
from modules.downloader import stream_video

app = Flask(__name__, static_folder="static", static_url_path="")


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
        return jsonify(info)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/download", methods=["GET", "POST"])
def download():
    if request.method == "GET":
        video_url = request.args.get("video_url", "").strip()
        title = request.args.get("title", "meta_ai_video")
        ext = request.args.get("ext", "mp4")
    else:
        data = request.get_json() or {}
        video_url = data.get("video_url", "").strip()
        title = data.get("title", "meta_ai_video")
        ext = data.get("ext", "mp4")

    if not video_url:
        return jsonify({"error": "No video_url provided"}), 400

    try:
        return stream_video(video_url, title, ext)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)  # 0.0.0.0 allows mobile on same Wi-Fi
