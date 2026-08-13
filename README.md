# Lenny Biography Portal History

```text
Version 2.5.1 "One-Click Portal Launcher":
Core & Backend:
- Added a root-level `run.bat` launcher to create the virtual environment, install dependencies, open the app, and launch the browser automatically.
- Wired the app startup flow so the catalog JSON and SQLite database are validated before the website renders, preventing broken startup states.
- Kept the Flask app, scanner, and template/static layers connected as a single working portal stack.

Version 2.5 "The Cloud Independence Update":
Core & Backend:
- Completely severed the application's reliance on Jellyfin. The engine is now 100% standalone!
- Integrated a live connection to The Movie Database (TMDB) using secure networking tools. This allows the portal to automatically fetch the latest movie details, ratings, and descriptions directly from the web in real-time, while keeping your private API keys safe and hidden.
- Built a hyper-efficient pipeline that autonomously downloads pure, uncompressed high-resolution Posters, Backdrops, and Actor Headshots natively via the internet. This should fix most broken thumbnails, remaining patches will be fixed in future updates.
- Removed over 160 lines of deprecated local-SQLite parsing and centralized the entire data flow into a cloud-first `portal_db.db` initialization sequence.

Version 2.0 "The Cinematic Engine":
Core & Backend:
- Upgraded the Python `scanner.py` to concurrently index multiple root libraries (Movies and Anime directories).
- Rewrote the Jellyfin metadata harvester to operate completely offline, querying the raw `jellyfin.db` cache directly via SQLite.
- Engineered cascading fuzzy-matching algorithms (stripping dates, "Season" tags, and Dub markers) to successfully salvage missing title correlations.
- Automatically isolates and duplicates highest-quality Jellyfin backdrops, posters, and cast headshots into local `static/` directories.

UI & Front-End Design:
- Redesigned the entire portal with a premium Dark-Glassmorphic responsive CSS Grid.
- Created a Master/Detail interface featuring cast rows, synopses, runtimes, ratings, and gorgeous UI fallbacks for unknown media.
- Implemented mathematical 3D Parallax mouse-tracking effects for movie cards, simulating physical glossy reflections.
- Built a lightweight native JS Canvas algorithm that reads the movie poster and dynamically theme-tints the glowing shadows of the entire page to match.
- Introduced infinite keyframe "breathing" animations for gigantic cinematic background elements.
- Utterly replaced default browser playback controls with a custom-engineered Video Player UX layer, fully optimized for Mobile breakpoints and Spacebar triggers!

Version 1.2:
Core:
- Reorganized the project into a cleaner Flask-style structure with backend, templates, static, and data folders.
- Updated the codebase to use file-location-based paths so the app keeps working after files are moved.
- Cleaned out obsolete root-level duplicates from the old layout.

App Structure:
- Flask now serves templates from templates/ and assets from static/.
- Movie catalog data is now read from data/Movies/movies.json through /api/catalog.
- SQLite now lives in backend/data/portal_db.db.

Fixes and Optimization:
- Fixed db_setup.py so the database schema now includes synopsis, cast_list, and genres before harvest() updates them.
- Added a small shared database connection helper in run_portal.py.
- Refreshed the README to match the new structure while preserving version tracking.

Files moved or created:
- backend/run_portal.py
- backend/db_setup.py
- backend/Movies/scanner.py
- backend/data/portal_db.db
- templates/index.html
- templates/movies.html
- static/css/style.css
- static/js/movies_app.js
- static/thumbnails/
- data/Movies/movies.json

Files removed from active structure:
- run_portal.py
- db_setup.py
- index.html
- style.css
- Movies/index.html
- Movies/app.js
- Movies/scanner.py
- old root movies.json copies

Version 1.10.02:
Documentation:
- Added project documentation and version tracking notes.

Version 1.10.01:
Minor changes

Version 1.10:
Playback:
- Added browser-based video playback for supported movie files.

New files:
- app.js (moved functions out of Movies/index.html for better organization and functionality)

Version 1:
Core:
- Established the Flask-Python bridge to connect the D: drive to the web.
- Implemented scanner.py to auto-generate movies.json, eliminating manual entry.

UI:
- Created the Master Portal landing page and a basic movie grid.
- Built a simple two-page website with a master portal and a movie catalog.

Files:
- .gitignore
- Movies/index.html
- Movies/scanner.py
- index.html
- movies.json
- run_portal.py
- style.css
```
