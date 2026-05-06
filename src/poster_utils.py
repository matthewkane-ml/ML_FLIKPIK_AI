"""
Poster helpers for the Streamlit movie recommender.

Best option: add a free TMDB API key as an environment variable named
TMDB_API_KEY. The app will fetch real posters automatically.

Fallback: if your dataset already has poster_url or poster_path columns,
those are used first. If nothing is available, the app shows a clean
placeholder poster instead of breaking.
"""

import os
from functools import lru_cache

import requests

TMDB_API_KEY = os.environ.get("c5a29fa482955c241150b9422368d922", "").strip()
TMDB_SEARCH_URL = "https://api.themoviedb.org/3/search/movie"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w342"


def _clean_title(title):
    if not isinstance(title, str):
        return ""
    if title.endswith(")") and "(" in title:
        return title.rsplit("(", 1)[0].strip()
    return title.strip()


def _from_row(movie_row):
    if movie_row is None:
        return None

    try:
        if "poster_url" in movie_row and isinstance(movie_row["poster_url"], str):
            value = movie_row["poster_url"].strip()
            if value.startswith("http"):
                return value

        if "poster_path" in movie_row and isinstance(movie_row["poster_path"], str):
            value = movie_row["poster_path"].strip()
            if value.startswith("http"):
                return value
            if value:
                return f"{TMDB_IMAGE_BASE}{value}"
    except Exception:
        return None

    return None


@lru_cache(maxsize=2048)
def fetch_tmdb_poster(title):
    """Fetch a poster URL from TMDB using a movie title."""
    clean_title = _clean_title(title)

    if not TMDB_API_KEY or not clean_title:
        return None

    try:
        response = requests.get(
            TMDB_SEARCH_URL,
            params={"api_key": TMDB_API_KEY, "query": clean_title, "include_adult": "false"},
            timeout=8,
        )
        response.raise_for_status()
        results = response.json().get("results", [])

        if not results:
            return None

        poster_path = results[0].get("poster_path")
        if poster_path:
            return f"{TMDB_IMAGE_BASE}{poster_path}"
    except Exception:
        return None

    return None


def get_poster_url(movie_row=None, title=None):
    """Return the best available poster URL for a movie."""
    row_poster = _from_row(movie_row)
    if row_poster:
        return row_poster

    if title:
        return fetch_tmdb_poster(title)

    try:
        row_title = movie_row.get("title")
    except Exception:
        row_title = None

    return fetch_tmdb_poster(row_title) if row_title else None


def poster_caption(title):
    return f"Poster for {title}" if title else "Movie poster"
