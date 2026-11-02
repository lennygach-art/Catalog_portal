"""Scan configured media roots and sync changed catalog entries to SQLite."""

import threading

from Movies.scanner import scan_movies
from db_setup import harvest, setup_database

_CATALOG_SYNC_LOCK = threading.RLock()


def harvest_missing_metadata():
    """Fetch missing thumbnails and details without overlapping catalog writes."""
    with _CATALOG_SYNC_LOCK:
        harvest(only_missing=True)


def update_catalog(force=False, refresh_missing_metadata=False, harvest_metadata=True):
    """Sync catalog changes and return whether the scanned catalog changed."""
    with _CATALOG_SYNC_LOCK:
        movies, scanned_roots, changed = scan_movies()
        if movies is None:
            return False

        if not changed and not force:
            if refresh_missing_metadata and harvest_metadata:
                harvest(only_missing=True)
            return False

        # Passing scanned roots removes database rows for folders that were deleted.
        setup_database(scanned_roots)
        if harvest_metadata:
            harvest(only_missing=True)
        return changed


if __name__ == "__main__":
    update_catalog()
