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


def get_media_dirs():
    configured_dirs = os.getenv("MOVIES_MEDIA_DIRS")
    if configured_dirs:
        return [Path(path.strip()) for path in configured_dirs.split(";") if path.strip()]
    return DEFAULT_MEDIA_DIRS


def clean_movie_name(folder_name):
    ignore_list = ["Downloading", "aWatched", "WebToolTip"]
    if any(item in folder_name for item in ignore_list):
        return None, None, "Ignore"

    season_pattern = r"^(.*?)[\s\.\(\[]+([sS]\d+|[sS]eason\s*\d+)"
    year_pattern = r"^(.*?)[\s\.\(\[]+(\d{4})"

    match_season = re.search(season_pattern, folder_name)
    if match_season:
        title = match_season.group(1).replace(".", " ").strip(" .([")
        title = re.sub(r"\(\d{4}\)", "", title).strip()
        return title, match_season.group(2).upper(), "TV Show"

    match_year = re.search(year_pattern, folder_name)
    if match_year:
        title = match_year.group(1).replace(".", " ").strip(" .([")
        return title, match_year.group(2), "Movie"

    clean_title = folder_name.replace(".", " ").strip()
    return clean_title, "Unknown", "Other"


def scan_movies():
    movie_list = []
    scanned_roots = []
    media_dirs = get_media_dirs()
    
    for folder_path in media_dirs:
        print(f"--- Starting Scan: {folder_path} ---\n")

        if not folder_path.is_dir():
            print(f" Error: Could not find path {folder_path}")
            continue
        scanned_roots.append(folder_path.resolve())

        for entry in folder_path.iterdir():
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
        return None, []

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with DATABASE_FILE.open("w", encoding="utf-8") as file:
        json.dump(movie_list, file, indent=4)

    print(f"\n---  Success! {len(movie_list)} items saved to {DATABASE_FILE} ---")
    return movie_list, scanned_roots


if __name__ == "__main__":
    scan_movies()
