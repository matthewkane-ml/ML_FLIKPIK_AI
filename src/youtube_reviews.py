import os
import requests
from urllib.parse import quote_plus

YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")
YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"


def get_youtube_trailer(title: str):
    """
    Fetch a real YouTube trailer/review video using YouTube Data API v3.
    Returns a dict with title, video_id, url, thumbnail.
    """
    if not YOUTUBE_API_KEY:
        return None

    query = f"{title} official trailer movie"

    params = {
        "part": "snippet",
        "q": query,
        "key": YOUTUBE_API_KEY,
        "type": "video",
        "maxResults": 1,
        "videoEmbeddable": "true",
        "safeSearch": "moderate",
    }

    try:
        response = requests.get(YOUTUBE_SEARCH_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        items = data.get("items", [])
        if not items:
            return None

        item = items[0]
        video_id = item["id"]["videoId"]
        snippet = item["snippet"]

        return {
            "video_id": video_id,
            "title": snippet.get("title", ""),
            "channel": snippet.get("channelTitle", ""),
            "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "embed_url": f"https://www.youtube.com/embed/{video_id}?autoplay=1&mute=1&controls=1",
        }

    except Exception:
        return None


def get_youtube_search_url(title: str):
    query = quote_plus(f"{title} movie trailer review")
    return f"https://www.youtube.com/results?search_query={query}"
