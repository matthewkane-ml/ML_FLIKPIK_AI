import os
import sys
import math
import random
import requests
from urllib.parse import quote_plus

import pandas as pd
import streamlit as st

# ----------------------------------------------------------
# PATH SETUP
# ----------------------------------------------------------
APP_DIR = os.path.dirname(__file__)
BASE_DIR = os.path.abspath(os.path.join(APP_DIR, ".."))
SRC_DIR = os.path.join(BASE_DIR, "src")

if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

# ----------------------------------------------------------
# IMPORT PROJECT MODULES
# ----------------------------------------------------------
from config import (
    MODEL_PATH,
    USER_RATINGS_PATH,
    RECOMMENDER_PARAMS,
    DEFAULT_TOP_N
)

from data_loader import load_processed_data
from recommender import HybridRecommender
from user_profiles import UserProfileStore
from search_engine import MovieSearchEngine
from chatbot import MovieChatbot
from metrics import compare_models
from poster_utils import get_poster_url

# ----------------------------------------------------------
# PAGE CONFIG
# ----------------------------------------------------------
st.set_page_config(
    page_title="Movie Recommender 5.0",
    page_icon="🎬",
    layout="wide"
)


# ----------------------------------------------------------
# CUSTOM UI STYLES
# ----------------------------------------------------------
def inject_custom_css():
    st.markdown(
        """
        <style>
            .stApp {
                background: linear-gradient(135deg, #070707 0%, #141414 45%, #220b0b 100%);
                color: #f5f5f5;
            }
            [data-testid="stSidebar"] {
                background: rgba(10, 10, 10, 0.95);
                border-right: 1px solid rgba(255,255,255,0.08);
            }
            .hero {
                padding: 2rem;
                border-radius: 26px;
                background: linear-gradient(135deg, rgba(229,9,20,0.95), rgba(20,20,20,0.92));
                box-shadow: 0 20px 60px rgba(0,0,0,0.35);
                margin-bottom: 1.2rem;
            }
            .hero h1 {
                font-size: 3rem;
                margin-bottom: 0.2rem;
                color: white;
            }
            .hero p {
                font-size: 1.05rem;
                color: #f1f1f1;
                max-width: 850px;
            }
            .movie-card {
                min-height: 430px;
                padding: 0.8rem;
                border-radius: 22px;
                background: rgba(255,255,255,0.065);
                border: 1px solid rgba(255,255,255,0.10);
                box-shadow: 0 14px 32px rgba(0,0,0,0.25);
                transition: transform .18s ease, border-color .18s ease, background .18s ease;
                overflow: hidden;
            }
            .movie-card:hover {
                transform: translateY(-5px);
                border-color: rgba(229,9,20,0.7);
                background: rgba(255,255,255,0.10);
            }
            .movie-title {
                font-weight: 800;
                font-size: 1rem;
                line-height: 1.2;
                margin-top: 0.65rem;
                color: #ffffff;
            }
            .movie-meta {
                font-size: 0.78rem;
                color: #cfcfcf;
                min-height: 38px;
            }
            .pill {
                display: inline-block;
                padding: 0.22rem 0.52rem;
                margin: 0.12rem 0.12rem 0.12rem 0;
                border-radius: 999px;
                background: rgba(229,9,20,0.20);
                border: 1px solid rgba(229,9,20,0.40);
                color: #fff;
                font-size: 0.72rem;
            }
            .score-line {
                color: #f8d7da;
                font-size: 0.8rem;
                margin-top: 0.4rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero():
    st.markdown(
        """
        <div class="hero">
            <h1>🎬 Movie Recommender 6.0</h1>
            <p>Netflix-style recommendations with posters, streaming badges, social buzz, trailers, model metrics, and a cleaner product-ready layout.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def shorten(text, max_len=72):
    text = "" if text is None else str(text)
    return text if len(text) <= max_len else text[: max_len - 3] + "..."


def placeholder_poster(title):
    from urllib.parse import quote_plus
    safe_title = quote_plus(clean_movie_title(title) or "Movie")
    return f"https://placehold.co/342x513/141414/FFFFFF?text={safe_title}"

# ----------------------------------------------------------
# CACHE LOADERS
# ----------------------------------------------------------
@st.cache_data
def cached_data():
    return load_processed_data()

@st.cache_resource
def cached_model(train, movies, genres):

    if os.path.exists(MODEL_PATH):
        try:
            return HybridRecommender.load(MODEL_PATH)
        except:
            pass

    model = HybridRecommender(
        train_df=train,
        movies_df=movies,
        genre_df=genres,
        **RECOMMENDER_PARAMS
    ).fit()

    model.save(MODEL_PATH)
    return model

# ----------------------------------------------------------
# MOCK LIVE FEATURES
# Replace with APIs later
# ----------------------------------------------------------
def get_streaming(title):

    platforms = [
        "Netflix",
        "Prime Video",
        "Max",
        "Hulu",
        "Disney+",
        "Peacock",
        "Paramount+"
    ]

    random.seed(abs(hash(title)) % 100000)
    n = random.randint(1, 3)
    return random.sample(platforms, n)

def get_social(title):

    random.seed(abs(hash(title)) % 100000)

    return {
        "X": random.randint(1000, 40000),
        "Reddit": random.randint(500, 12000),
        "Facebook": random.randint(1000, 25000),
        "Instagram": random.randint(2000, 55000)
    }

def get_sentiment(title):

    random.seed(abs(hash(title)) % 100000)
    return random.randint(74, 97)

YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")
YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"

def clean_movie_title(title):

    if not isinstance(title, str):
        return ""

    # Converts titles like "Toy Story (1995)" into "Toy Story"
    if title.endswith(")") and "(" in title:
        return title.rsplit("(", 1)[0].strip()

    return title.strip()

def get_youtube_search_url(title):

    clean_title = clean_movie_title(title)
    query = quote_plus(f"{clean_title} movie trailer review")
    return f"https://www.youtube.com/results?search_query={query}"

def get_youtube_trailer(title):

    if not YOUTUBE_API_KEY:
        return None

    clean_title = clean_movie_title(title)

    params = {
        "part": "snippet",
        "q": f"{clean_title} official movie trailer",
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
            "title": snippet.get("title", ""),
            "channel": snippet.get("channelTitle", ""),
            "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
            "url": f"https://www.youtube.com/watch?v={video_id}",
        }

    except Exception as e:
        st.caption(f"YouTube API unavailable: {e}")
        return None

def hype_score(title):

    buzz = get_social(title)
    mentions = sum(buzz.values())
    sentiment = get_sentiment(title)

    score = (
        (mentions / 130000) * 0.60 +
        (sentiment / 100) * 0.40
    ) * 100

    return round(score, 2)

# ----------------------------------------------------------
# DISPLAY HELPERS
# ----------------------------------------------------------
def show_movie_table(df, limit=20):

    if df is None or df.empty:
        st.info("No results found.")
        return

    st.dataframe(df.head(limit), use_container_width=True)

def show_movie_cards(df, score_col=None, max_items=24):

    if df is None or df.empty:
        st.info("No movies found.")
        return

    records = df.head(max_items).to_dict("records")
    cols_per_row = 4

    for row_start in range(0, len(records), cols_per_row):
        cols = st.columns(cols_per_row)

        for col, row in zip(cols, records[row_start: row_start + cols_per_row]):
            title = row.get("title", "Unknown")
            genres = row.get("genres", "")
            movie_id = row.get("movieId", "")
            poster = get_poster_url(row, title=title) or placeholder_poster(title)
            stream = get_streaming(title)
            total_buzz = sum(get_social(title).values())

            score_html = ""
            if score_col and score_col in row:
                try:
                    score_html = f"<div class='score-line'>⭐ {score_col}: {float(row[score_col]):.3f}</div>"
                except Exception:
                    score_html = ""

            platform_html = "".join([f"<span class='pill'>{p}</span>" for p in stream[:3]])

            with col:
                st.markdown("<div class='movie-card'>", unsafe_allow_html=True)
                st.image(poster, use_container_width=True)
                st.markdown(
                    f"""
                    <div class='movie-title'>{shorten(title, 58)}</div>
                    <div class='movie-meta'>{shorten(genres, 72)}</div>
                    <div>{platform_html}</div>
                    {score_html}
                    <div class='score-line'>🔥 Hype: {hype_score(title)} | 💬 {total_buzz:,} mentions</div>
                    <div class='score-line'>Movie ID: {movie_id}</div>
                    """,
                    unsafe_allow_html=True,
                )
                st.link_button("▶️ Trailer / Reviews", get_youtube_search_url(title), use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

# ----------------------------------------------------------
# MAIN APP
# ----------------------------------------------------------
def main():

    inject_custom_css()
    render_hero()

    st.caption("Hybrid AI + Social Buzz + Streaming + Analytics")

    # ------------------------------------------
    # LOAD DATA
    # ------------------------------------------
    try:
        train, val, test, movies, genres = cached_data()
    except Exception as e:
        st.error(str(e))
        st.stop()

    model = cached_model(train, movies, genres)

    search_engine = MovieSearchEngine(movies)
    chatbot = MovieChatbot(model=model, movies_df=movies)
    profile_store = UserProfileStore(USER_RATINGS_PATH)

    # ------------------------------------------
    # SIDEBAR
    # ------------------------------------------
    with st.sidebar:

        st.header("👤 Profile")

        users = profile_store.get_users()
        default_user = users[0] if users else "brandon"

        username = st.text_input("Username", default_user)

        st.divider()

        top_n = st.slider("Recommendations", 5, 25, DEFAULT_TOP_N)

        display = st.radio(
            "Display Mode",
            ["Cards", "Table"],
            horizontal=True
        )

        st.divider()

        st.header("📊 Dataset")
        st.write(f"Movies: **{movies.shape[0]:,}**")
        st.write(f"Ratings: **{train.shape[0]:,}**")
        st.write(f"Users: **{train['userId'].nunique():,}**")

    # ------------------------------------------
    # TABS
    # ------------------------------------------
    tabs = st.tabs([
        "🏠 Home",
        "🔎 Search",
        "🎞 Similar",
        "🎯 My Recs",
        "⭐ Rate Movies",
        "📺 Streaming",
        "📱 Social Buzz",
        "▶️ YouTube",
        "📊 Metrics",
        "🤖 AI Assistant",
        "👤 Insights"
    ])

    # ------------------------------------------
    # HOME
    # ------------------------------------------
    with tabs[0]:

        st.header("🔥 Trending Right Now")

        trending = model.popularity_df.copy()
        trending["hype"] = trending["title"].apply(hype_score)

        trending = trending.sort_values(
            ["hype", "weighted_score"],
            ascending=False
        )

        if display == "Cards":
            show_movie_cards(trending, "hype")
        else:
            show_movie_table(trending)

    # ------------------------------------------
    # SEARCH
    # ------------------------------------------
    with tabs[1]:

        st.header("🔎 Search Movies")

        q = st.text_input("Title contains")

        results = search_engine.search(
            title_query=q,
            genre="All",
            min_year="",
            max_year="",
            limit=100
        )

        if display == "Cards":
            show_movie_cards(results)
        else:
            show_movie_table(results)

    # ------------------------------------------
    # SIMILAR
    # ------------------------------------------
    with tabs[2]:

        st.header("🎞 Similar Movie Finder")

        q = st.text_input("Search movie", "Toy Story")

        matches = search_engine.title_matches(q, limit=20)

        if not matches.empty:

            chosen = st.selectbox(
                "Choose Movie",
                matches["title"].tolist()
            )

            movie_id = int(
                matches.loc[
                    matches["title"] == chosen,
                    "movieId"
                ].iloc[0]
            )

            similar = model.get_similar_movies(
                movie_id,
                n_neighbors=top_n
            )

            if display == "Cards":
                show_movie_cards(similar, "similarity")
            else:
                show_movie_table(similar)

    # ------------------------------------------
    # RECOMMENDATIONS
    # ------------------------------------------
    with tabs[3]:

        st.header("🎯 Personalized Recommendations")

        try:
            recs = model.recommend_hybrid(
                user_id=1,
                top_n=top_n
            )
        except:
            recs = model._popularity_fallback(top_n=top_n)

        if display == "Cards":
            show_movie_cards(recs, "final_score")
        else:
            show_movie_table(recs)

    # ------------------------------------------
    # RATE MOVIES
    # ------------------------------------------
    with tabs[4]:

        st.header("⭐ Build Your Profile")

        q = st.text_input("Search movie to rate", "Matrix")

        matches = search_engine.title_matches(q, limit=20)

        if not matches.empty:

            selected = st.selectbox(
                "Choose title",
                matches["title"].tolist()
            )

            rating = st.slider(
                "Your Rating",
                1.0, 5.0, 4.0, 0.5
            )

            if st.button("Save Rating"):

                movie_id = int(
                    matches.loc[
                        matches["title"] == selected,
                        "movieId"
                    ].iloc[0]
                )

                profile_store.add_or_update_rating(
                    username=username,
                    movie_id=movie_id,
                    title=selected,
                    rating=rating
                )

                st.success("Rating saved.")

    # ------------------------------------------
    # STREAMING
    # ------------------------------------------
    with tabs[5]:

        st.header("📺 Where To Watch")

        movie = st.selectbox(
            "Select Movie",
            movies["title"].dropna().unique()
        )

        for p in get_streaming(movie):
            st.success(p)

    # ------------------------------------------
    # SOCIAL BUZZ
    # ------------------------------------------
    with tabs[6]:

        st.header("📱 Social Buzz")

        movie = st.selectbox(
            "Movie",
            movies["title"].dropna().unique(),
            key="buzz"
        )

        buzz = get_social(movie)

        c1, c2, c3, c4 = st.columns(4)

        c1.metric("X", buzz["X"])
        c2.metric("Reddit", buzz["Reddit"])
        c3.metric("Facebook", buzz["Facebook"])
        c4.metric("Instagram", buzz["Instagram"])

        st.subheader("Audience Sentiment")
        st.progress(get_sentiment(movie) / 100)

    # ------------------------------------------
    # YOUTUBE
    # ------------------------------------------
    with tabs[7]:

        st.header("▶️ Reviews & Blogs")

        movie = st.selectbox(
            "Movie Title",
            movies["title"].dropna().unique(),
            key="yt"
        )

        trailer = get_youtube_trailer(movie)

        if trailer:
            st.write(f"Trailer for **{movie}**")
            st.caption(f"{trailer['title']} | Channel: {trailer['channel']}")

            # Autoplay works best when muted because most browsers block unmuted autoplay.
            st.video(
                trailer["url"],
                autoplay=True,
                muted=True
            )

            st.markdown(f"[Open on YouTube]({trailer['url']})")
        else:
            search_url = get_youtube_search_url(movie)

            if not YOUTUBE_API_KEY:
                st.info("Add a YOUTUBE_API_KEY environment variable to fetch real trailers automatically.")
            else:
                st.warning("No trailer found from the YouTube API.")

            st.markdown(f"[🔎 Search YouTube for {movie}]({search_url})")

    # ------------------------------------------
    # METRICS
    # ------------------------------------------
    with tabs[8]:

        st.header("📊 Model Evaluation")

        sample_users = st.slider(
            "Sample Users",
            25, 200, 100, 25
        )

        if st.button("Run Evaluation"):

            with st.spinner("Running..."):

                results = compare_models(
                    model=model,
                    val_df=val,
                    test_df=test,
                    top_n=top_n,
                    min_eval_rating=4.0,
                    sample_users=sample_users
                )

            st.dataframe(results, use_container_width=True)

    # ------------------------------------------
    # AI ASSISTANT
    # ------------------------------------------
    with tabs[9]:

        st.header("🤖 AI Movie Assistant")

        prompt = st.text_area(
            "What do you want to watch?",
            "Recommend exciting sci-fi movies"
        )

        if st.button("Ask Assistant"):

            response, recs = chatbot.recommend(
                prompt,
                top_n=top_n
            )

            st.write(response)

            if display == "Cards":
                show_movie_cards(recs, "weighted_score")
            else:
                show_movie_table(recs)

    # ------------------------------------------
    # INSIGHTS
    # ------------------------------------------
    with tabs[10]:

        st.header("👤 User Insights")

        ratings = profile_store.get_user_ratings(username)

        if ratings.empty:
            st.info("Rate movies first.")
        else:
            c1, c2, c3 = st.columns(3)

            c1.metric("Movies Rated", len(ratings))
            c2.metric(
                "Average Rating",
                round(ratings["rating"].mean(), 2)
            )
            c3.metric(
                "Highest",
                round(ratings["rating"].max(), 2)
            )

            st.dataframe(ratings, use_container_width=True)

    st.markdown("---")
    st.caption("Movie Recommender 6.0 | Netflix-Style UI | Deploy Ready")

# ----------------------------------------------------------
# RUN
# ----------------------------------------------------------
if __name__ == "__main__":
    main()