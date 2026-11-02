from flask import Flask, jsonify, render_template, request, send_file
import mimetypes
import os
from pathlib import Path
import sqlite3
import subprocess
import threading
import time
import webbrowser

from catalog_sync import harvest_missing_metadata, update_catalog

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "templates"
STATIC_DIR = PROJECT_ROOT / "static"
DATA_DIR = PROJECT_ROOT / "data"
MOVIES_DATA_FILE = DATA_DIR / "Movies" / "movies.json"
DATABASE_PATH = Path(__file__).resolve().parent / "data" / "portal_db.db"
PORT = 5000
CATALOG_SCAN_INTERVAL_SECONDS = 60
METADATA_RETRY_INTERVAL_SECONDS = 6 * 60 * 60
CATALOG_WATCHER_STOP = threading.Event()
VIDEO_MIME_TYPES = {
    ".avi": "video/x-msvideo",
    ".m2ts": "video/mp2t",
    ".m4v": "video/mp4",
    ".mkv": "video/x-matroska",
    ".mov": "video/quicktime",
    ".mp4": "video/mp4",
    ".mpeg": "video/mpeg",
    ".mpg": "video/mpeg",
    ".ts": "video/mp2t",
    ".webm": "video/webm",
    ".wmv": "video/x-ms-wmv",
}

app = Flask(__name__, template_folder=str(TEMPLATES_DIR), static_folder=str(STATIC_DIR))


def ensure_catalog_data(
    force=False,
    refresh_missing_metadata=False,
    harvest_metadata=True,
):
    try:
        return update_catalog(
            force=force,
            refresh_missing_metadata=refresh_missing_metadata,
            harvest_metadata=harvest_metadata,
        )
    except Exception as exc:
        print(f"Catalog refresh failed; keeping the existing catalog: {exc}")
        return False


def watch_catalog_changes():
    try:
        interval = max(
            10,
            int(os.getenv("CATALOG_SCAN_INTERVAL_SECONDS", CATALOG_SCAN_INTERVAL_SECONDS)),
        )
    except ValueError:
        interval = CATALOG_SCAN_INTERVAL_SECONDS

    try:
        metadata_interval = max(
            interval,
            int(
                os.getenv(
                    "METADATA_RETRY_INTERVAL_SECONDS",
                    METADATA_RETRY_INTERVAL_SECONDS,
                )
            ),
        )
    except ValueError:
        metadata_interval = METADATA_RETRY_INTERVAL_SECONDS
    last_metadata_check = time.monotonic()

    while not CATALOG_WATCHER_STOP.wait(interval):
        changed = ensure_catalog_data()
        now = time.monotonic()
        if changed:
            last_metadata_check = now
        elif now - last_metadata_check >= metadata_interval:
            ensure_catalog_data(refresh_missing_metadata=True)
            last_metadata_check = now


def start_catalog_watcher():
    watcher = threading.Thread(
        target=watch_catalog_changes,
        name="catalog-change-watcher",
        daemon=True,
    )
    watcher.start()


def start_metadata_harvester():
    def harvest_in_background():
        try:
            harvest_missing_metadata()
        except Exception as exc:
            print(f"Background thumbnail refresh failed: {exc}")

    harvester = threading.Thread(
        target=harvest_in_background,
        name="metadata-harvester",
        daemon=True,
    )
    harvester.start()


def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/movies-catalog")
def movies_page():
    return render_template("movies.html")


@app.route("/api/catalog")
def get_catalog():
    if not MOVIES_DATA_FILE.exists():
        return jsonify([])

    return send_file(MOVIES_DATA_FILE, mimetype="application/json")


@app.route("/open-folder")
def open_folder():
    folder_path = request.args.get("path")
    if folder_path:
        subprocess.Popen(["explorer", folder_path])
        return "OK", 200
    return "Error", 400


@app.route("/list-contents")
def list_contents():
    folder_path = request.args.get("path")
    if not folder_path:
        return jsonify({"error": "Missing path"}), 400

    target = Path(folder_path)
    if not target.is_dir():
        return jsonify({"error": "Folder not found"}), 404

    try:
        files = sorted(item.name for item in target.iterdir())
        return jsonify({"files": files})
    except OSError as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/stream-video")
def stream_video():
    video_path = request.args.get("path")
    if not video_path:
        return "Video not found", 404

    if os.sep == "/":
        video_path = video_path.replace("\\", "/")

    target = Path(video_path)
    if not target.exists():
        print(f"Error: Video not found at {video_path}")
        return "Video not found", 404

    guessed_type, _ = mimetypes.guess_type(str(target))
    return send_file(
        target,
        conditional=True,
        mimetype=(
            guessed_type
            or VIDEO_MIME_TYPES.get(target.suffix.lower())
            or "application/octet-stream"
        ),
    )


@app.route("/toggle-favorite", methods=["POST"])
def toggle_favorite():
    movie_id = request.args.get("id")
    if not movie_id:
        return jsonify({"error": "Missing movie id"}), 400
    return "OK", 200


@app.route("/get-movies")
def get_movies():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM movies")
    rows = cursor.fetchall()
    movies = [dict(row) for row in rows]
    conn.close()
    return jsonify(movies)


if __name__ == "__main__":
    ensure_catalog_data(force=True, harvest_metadata=False)
    start_metadata_harvester()
    start_catalog_watcher()
    webbrowser.open(f"http://localhost:{PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=False)
