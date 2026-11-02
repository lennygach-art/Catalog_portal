import json
import os
from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data" / "Movies"
DATABASE_FILE = DATA_DIR / "movies.json"
DEFAULT_MEDIA_DIRS = [
    Path(r"E:\Win_Vault\Movies"),
    Path(r"E:\Win_Vault\Anime"),
]
VIDEO_EXTENSIONS = {
    ".avi",
    ".m2ts",
    ".m4v",
    ".mkv",
    ".mov",
    ".mp4",
    ".mpeg",
    ".mpg",
    ".ts",
    ".webm",
    ".wmv",
}


def get_media_dirs():
    configured_dirs = os.getenv("MOVIES_MEDIA_DIRS")
    if configured_dirs:
        return [Path(path.strip()) for path in configured_dirs.split(";") if path.strip()]
    return DEFAULT_MEDIA_DIRS


def clean_movie_name(folder_name):
    ignore_list = ["Downloading", "aWatched", "WebToolTip"]
    if any(item in folder_name for item in ignore_list):
        return None, None, "Ignore"

    season_pattern = re.compile(
        r"(?i)(?:^|[\s._(\[])(?:S(?P<s_season>\d{1,2})|"
        r"Season[\s._-]*(?P<named_season>\d{1,2}))"
        r"(?=$|[\s._)\]+-])"
    )
    year_pattern = re.compile(r"\b(19\d{2}|20\d{2})\b")
    release_pattern = re.compile(
        r"(?i)(?:^|[\s._(\[])(?:complete|proper|repack|limited|internal|"
        r"readnfo|720p|1080p|2160p|480p|4k|uhd|web[ ._-]?dl|web[ ._-]?rip|"
        r"blu[ ._-]?ray|bluray|brrip|hdrip|dvdrip|hdtv|nf|amzn|atvp|dsnp|"
        r"hbo|hmax|x26[45]|h\.?26[45]|hevc|av1|aac|ddp|dts|esubs?|multi)"
        r"(?=$|[\s._)\]-])"
    )

    season_match = season_pattern.search(folder_name)
    year_match = year_pattern.search(folder_name)
    release_match = release_pattern.search(folder_name)

    if season_match:
        title_end = season_match.start()
        season_number = season_match.group("s_season") or season_match.group(
            "named_season"
        )
        title_source = folder_name[:title_end]
        year_match = year_pattern.search(title_source)
        year_or_season = f"S{int(season_number):02d}"
        media_type = "TV Show"
    elif year_match:
        title_source = folder_name[: year_match.start()]
        year_or_season = year_match.group(1)
        media_type = "Movie"
    else:
        title_end = release_match.start() if release_match else len(folder_name)
        title_source = folder_name[:title_end]
        year_or_season = "Unknown"
        media_type = "Other"

    title = re.sub(r"\b(?:19|20)\d{2}\b", "", title_source)
    title = re.sub(r"[._]+", " ", title)
    title = re.sub(r"\s+", " ", title).strip(" -_.()[]")
    return title or folder_name, year_or_season, media_type


def scan_movies():
    movie_list = []
    scanned_roots = []
    media_dirs = get_media_dirs()

    missing_dirs = [folder for folder in media_dirs if not folder.is_dir()]
    if missing_dirs:
        print(
            "Catalog scan skipped because configured media directories are "
            f"unavailable: {', '.join(str(path) for path in missing_dirs)}"
        )
        return None, [], False

    for folder_path in media_dirs:
        print(f"--- Starting Scan: {folder_path} ---\n")
        scanned_roots.append(folder_path.resolve())

        for entry in folder_path.iterdir():
            if entry.is_file() and entry.suffix.lower() in VIDEO_EXTENSIONS:
                movie_list.append(
                    {
                        "display_name": entry.stem,
                        "year_or_season": "Video file",
                        "type": "Video",
                        "folder_name": entry.name,
                        "full_path": str(entry),
                    }
                )
                print(f" Found root-level video: {entry.name}")
                continue

            if not entry.is_dir():
                continue

            title, year_or_season, media_type = clean_movie_name(entry.name)
            if media_type == "Ignore":
                print(f" Skipping: {entry.name}")
                continue

            movie_data = {
                "display_name": title,
                "year_or_season": year_or_season,
                "type": media_type,
                "folder_name": entry.name,
                "full_path": str(entry),
            }
            movie_list.append(movie_data)
            print(f" Found {media_type}: {title} ({year_or_season})")

    if not scanned_roots:
        print("No configured media directories were available; keeping the existing catalog.")
        return None, [], False

    movie_list.sort(key=lambda movie: os.path.normcase(movie["full_path"]))

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with DATABASE_FILE.open("r", encoding="utf-8") as file:
            existing_movies = json.load(file)
    except (OSError, json.JSONDecodeError):
        existing_movies = None

    if movie_list == existing_movies:
        print(f"Catalog unchanged; {len(movie_list)} items are already indexed.")
        return movie_list, scanned_roots, False

    with DATABASE_FILE.open("w", encoding="utf-8") as file:
        json.dump(movie_list, file, indent=4)

    print(f"\n--- Catalog changed: {len(movie_list)} items saved to {DATABASE_FILE} ---")
    return movie_list, scanned_roots, True


if __name__ == "__main__":
    scan_movies()
