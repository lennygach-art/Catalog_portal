from flask import Flask, jsonify, render_template, request, send_file
import mimetypes
import os
from pathlib import Path
import sqlite3
import subprocess
import webbrowser

from Movies.scanner import scan_movies
from db_setup import harvest, setup_database

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "templates"
STATIC_DIR = PROJECT_ROOT / "static"
DATA_DIR = PROJECT_ROOT / "data"
MOVIES_DATA_FILE = DATA_DIR / "Movies" / "movies.json"
DATABASE_PATH = Path(__file__).resolve().parent / "data" / "portal_db.db"
PORT = 5000

app = Flask(__name__, template_folder=str(TEMPLATES_DIR), static_folder=str(STATIC_DIR))


def ensure_catalog_data():
    try:
        scanned_movies, scanned_roots = scan_movies()
        setup_database(scanned_roots if scanned_movies is not None else None)
    except (OSError, ValueError, sqlite3.Error) as exc:
        print(f"Catalog scan/sync failed; keeping existing database where possible: {exc}")
        setup_database()
        return

    try:
        harvest(only_missing=True)
    except Exception as exc:
        print(f"Metadata harvest failed; the portal will still start: {exc}")


ensure_catalog_data()


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
        # Frontend joins folder + file with a Windows backslash; fix for Linux/Docker
        video_path = video_path.replace("\\", "/")

    target = Path(video_path)
    if not target.exists():
        print(f"Error: Video not found at {video_path}")
        return "Video not found", 404

    guessed_type, _ = mimetypes.guess_type(str(target))
    return send_file(
        target,
        conditional=True,
        mimetype=guessed_type or "application/octet-stream",
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
    webbrowser.open(f"http://localhost:{PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=False)
