import json
import os
from pathlib import Path
import sqlite3

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
MOVIES_JSON_PATH = DATA_DIR / "Movies" / "movies.json"
DATABASE_PATH = BACKEND_DIR / "data" / "portal_db.db"
THUMBNAILS_DIR = PROJECT_ROOT / "static" / "thumbnails"

JELLYFIN_URL = "http://localhost:8096"
API_KEY = "YOUR_API_KEY"
USER_ID = "YOUR_USER_ID"


def setup_database(scanned_roots=None):
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            display_name TEXT,
            year TEXT,
            type TEXT,
            full_path TEXT UNIQUE,
            thumbnail TEXT,
            synopsis TEXT,
            cast_list TEXT,
            genres TEXT,
            is_favorite INTEGER DEFAULT 0,
            last_position INTEGER DEFAULT 0
        )
        """
    )
    
    new_columns = {
        "backdrop": "TEXT",
        "tagline": "TEXT",
        "official_rating": "TEXT",
        "community_rating": "REAL",
        "runtime": "INTEGER"
    }
    for col, dtype in new_columns.items():
        try:
            cursor.execute(f"ALTER TABLE movies ADD COLUMN {col} {dtype}")
        except sqlite3.OperationalError:
            pass


    if MOVIES_JSON_PATH.exists():
        with MOVIES_JSON_PATH.open("r", encoding="utf-8") as file:
            movies_data = json.load(file)

        for movie in movies_data:
            cursor.execute(
                """
                INSERT INTO movies (display_name, year, type, full_path)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(full_path) DO UPDATE SET
                    display_name = excluded.display_name,
                    year = excluded.year,
                    type = excluded.type
                """,
                (
                    movie["display_name"],
                    movie["year_or_season"],
                    movie["type"],
                    movie["full_path"],
                ),
            )

        if scanned_roots is not None:
            normalized_roots = [
                os.path.normcase(os.path.abspath(root)) for root in scanned_roots
            ]
            scanned_paths = {
                os.path.normcase(os.path.abspath(movie["full_path"]))
                for movie in movies_data
                if movie.get("full_path")
            }
            cursor.execute("SELECT id, full_path FROM movies WHERE full_path IS NOT NULL")
            stale_ids = []
            for movie_id, full_path in cursor.fetchall():
                normalized_path = os.path.normcase(os.path.abspath(full_path))
                if normalized_path in scanned_paths:
                    continue
                for root in normalized_roots:
                    try:
                        if os.path.commonpath([root, normalized_path]) == root:
                            stale_ids.append((movie_id,))
                            break
                    except ValueError:
                        continue
            cursor.executemany("DELETE FROM movies WHERE id = ?", stale_ids)

    conn.commit()
    conn.close()
    print("Database synced with movies.json successfully!")


def harvest(only_missing=True):
    import os
    import re
    import requests
    from dotenv import load_dotenv

    # Load TMDB Key securely
    env_path = BACKEND_DIR / ".env"
    load_dotenv(env_path)
    TMDB_API_KEY = os.getenv("TMDB_API_KEY")
    if not TMDB_API_KEY:
        print("Error: TMDB_API_KEY not found. Please set it in backend/.env")
        return

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)
    CAST_DIR = PROJECT_ROOT / "static" / "cast"
    CAST_DIR.mkdir(parents=True, exist_ok=True)

    query = "SELECT id, display_name, year, type FROM movies"
    if only_missing:
        query += " WHERE thumbnail IS NULL OR thumbnail = '' OR synopsis IS NULL OR synopsis = ''"
    cursor.execute(query)
    local_movies = cursor.fetchall()

    for movie_id, name, year_str, media_type in local_movies:
        search_type = "movie"
        if media_type and ("series" in media_type.lower() or "anime" in media_type.lower() or "tv" in media_type.lower()):
            search_type = "tv"
            
        clean_name = re.sub(r'(?i)SEASON\s*\d+|English Dub|\b(20\d{2}|19\d{2})\b', '', name).strip()
        
        search_url = f"https://api.themoviedb.org/3/search/{search_type}"
        params = {"api_key": TMDB_API_KEY, "query": clean_name}
        
        try:
            res = requests.get(search_url, params=params, timeout=10)
            res.raise_for_status()
            results = res.json().get("results", [])
        except Exception as e:
            print(f"TMDB Search failed for {name}: {e}")
            continue
            
        if not results:
            # Fallback search by trying first 2 words if it's long
            first_words = " ".join(clean_name.split()[:2]) # type: ignore
            if len(first_words) > 3:
                try:
                    params["query"] = first_words
                    res = requests.get(search_url, params=params, timeout=10)
                    results = res.json().get("results", [])
                except:
                    pass
                    
        if not results:
            print(f"Skipping {name}: Not found on TMDB.")
            continue
            
        tmdb_item = results[0]
        tmdb_id = tmdb_item.get("id")
        
        # Details Endpoint
        details_url = f"https://api.themoviedb.org/3/{search_type}/{tmdb_id}"
        try:
            details_res = requests.get(
                details_url,
                params={"api_key": TMDB_API_KEY, "append_to_response": "credits,release_dates,content_ratings"},
                timeout=10,
            )
            details_res.raise_for_status()
            details = details_res.json()
        except:
            print(f"Failed to get details for {name}")
            continue
            
        synopsis = details.get("overview", "No description available.")
        tagline = details.get("tagline", "")
        comm_rating = details.get("vote_average", 0.0)
        
        runtime = details.get("runtime") or (details.get("episode_run_time")[0] if details.get("episode_run_time") else 0)
        genres = ", ".join([g.get("name") for g in details.get("genres", [])])
        
        off_rating = ""
        # Attempt to grab US certification gracefully
        if search_type == "movie" and "release_dates" in details:
            for r in details["release_dates"].get("results", []):
                if r.get("iso_3166_1") == "US":
                    dates = r.get("release_dates", [])
                    if dates and dates[0].get("certification"):
                        off_rating = dates[0].get("certification")
                        break
        elif search_type == "tv" and "content_ratings" in details:
            for r in details["content_ratings"].get("results", []):
                if r.get("iso_3166_1") == "US":
                    off_rating = r.get("rating", "")
                    break

        cast_data = details.get("credits", {}).get("cast", [])[:10]
        cast = []
        for c in cast_data:
            person_name = c.get("name")
            role = c.get("character")
            profile_path = c.get("profile_path")
            
            person_img_url = None
            if profile_path:
                img_url = f"https://image.tmdb.org/t/p/w185{profile_path}"
                dest_filename = f"{c.get('id')}.jpg"
                dest_path = CAST_DIR / dest_filename
                
                if not dest_path.exists():
                    try:
                        img_res = requests.get(img_url, timeout=5)
                        if img_res.status_code == 200:
                            with open(dest_path, "wb") as f:
                                f.write(img_res.content)
                    except:
                        pass
                person_img_url = dest_filename
                
            cast.append({"name": person_name, "role": role or "Actor", "image": person_img_url})
            
        cast_json = json.dumps(cast)
        
        poster_path = details.get("poster_path")
        backdrop_path = details.get("backdrop_path")
        
        img_dest_path = THUMBNAILS_DIR / f"tmdb_{tmdb_id}.jpg"
        bg_dest_path = THUMBNAILS_DIR / f"tmdb_{tmdb_id}_bg.jpg"
        
        if poster_path and not img_dest_path.exists():
            try:
                p_res = requests.get(f"https://image.tmdb.org/t/p/w500{poster_path}", timeout=10)
                if p_res.status_code == 200:
                    with open(img_dest_path, "wb") as f:
                        f.write(p_res.content)
            except: pass
            
        if backdrop_path and not bg_dest_path.exists():
            try:
                b_res = requests.get(f"https://image.tmdb.org/t/p/w1280{backdrop_path}", timeout=10)
                if b_res.status_code == 200:
                    with open(bg_dest_path, "wb") as f:
                        f.write(b_res.content)
            except: pass
            
        cursor.execute(
            """
            UPDATE movies
            SET thumbnail = ?, synopsis = ?, cast_list = ?, genres = ?,
                backdrop = ?, tagline = ?, official_rating = ?, community_rating = ?, runtime = ?
            WHERE id = ?
            """,
            (
                str(img_dest_path) if img_dest_path.exists() else None, 
                synopsis, cast_json, genres,
                str(bg_dest_path) if bg_dest_path.exists() else None,
                tagline, off_rating, comm_rating, runtime,
                movie_id
            ),
        )
        print(f"Harvested {name} natively from TMDB.")

    conn.commit()
    conn.close()
    print("Harvest Complete! Extracted metadata autonomously from TMDB API.")

if __name__ == "__main__":
    setup_database()
    harvest()
