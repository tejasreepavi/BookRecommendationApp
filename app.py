# -*- coding: utf-8 -*-
"""
app.py — BookRecommendationApp
AI-Powered Book Discovery using Collaborative Filtering + Google Books API

Run with:  streamlit run app.py
"""

import streamlit as st
import pandas as pd
import pickle
import numpy as np

from google_books import get_new_books, get_error_message

# ──────────────────────────────────────────────────────────────
# Page configuration  (must be the very first Streamlit call)
# ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="BookAI — Discover Your Next Read",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────────────
# CSS
# ──────────────────────────────────────────────────────────────
def _inject_css() -> None:
    try:
        with open("assets/style.css", encoding="utf-8") as fh:
            st.markdown(f"<style>{fh.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        pass  # Run without custom CSS rather than crashing

_inject_css()

# ──────────────────────────────────────────────────────────────
# Cached resource loaders  (loaded ONCE per Streamlit session)
# ──────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner="Loading recommendation model…")
def load_model() -> tuple:
    """
    Load the three pre-computed model files once per Streamlit session.
    Returns (pt, books_model, similarity_scores) or raises on missing files.
    """
    pt_loaded            = pickle.load(open("model/pt.pkl",                "rb"))
    books_loaded         = pickle.load(open("model/books.pkl",             "rb"))
    sim_scores_loaded    = pickle.load(open("model/similarity_scores.pkl", "rb"))
    return pt_loaded, books_loaded, sim_scores_loaded


@st.cache_data(show_spinner="Loading book catalog…")
def load_books_df() -> pd.DataFrame:
    """Load the full Books.csv catalog (read-only reference data)."""
    return pd.read_csv("Books.csv", low_memory=False)


# ──────────────────────────────────────────────────────────────
# Load data — with user-facing error if model files are missing
# ──────────────────────────────────────────────────────────────
try:
    pt, books_model, similarity_scores = load_model()
    books_df = load_books_df()
    _model_ok = True
except FileNotFoundError as exc:
    st.error(
        f"**Model files not found:** `{exc.filename}`\n\n"
        "Please run `python recommendation.py` to generate the model files, "
        "then restart the app."
    )
    st.stop()
except Exception as exc:
    st.error(f"**Failed to load model:** {exc}")
    st.stop()


# ──────────────────────────────────────────────────────────────
# Recommendation logic
# ──────────────────────────────────────────────────────────────
def recommend(book_name: str) -> list[dict]:
    """
    Return a list of up to 5 recommended books similar to *book_name*.

    Each item in the returned list is a dict with keys:
        title, author, image, preview, similarity

    ``similarity`` is the raw cosine similarity score (0–1).
    """
    matches = np.where(pt.index == book_name)[0]
    if len(matches) == 0:
        return []

    index = matches[0]

    similar_items = sorted(
        list(enumerate(similarity_scores[index])),
        key=lambda x: x[1],
        reverse=True,
    )[1:6]  # skip index 0 (self-match), take next 5

    recommended = []
    for idx, score in similar_items:
        matched = books_model[
            books_model["Book-Title"] == pt.index[idx]
        ].drop_duplicates("Book-Title")

        if matched.empty:
            continue

        row = matched.iloc[0]

        # Fetch preview link from Google Books — failure is non-fatal
        google_data = get_new_books(row["Book-Title"])
        preview = ""
        if "items" in google_data:
            try:
                info = google_data["items"][0]["volumeInfo"]
                preview = info.get("previewLink", "")
            except (IndexError, KeyError, TypeError):
                pass

        recommended.append({
            "title":      row["Book-Title"],
            "author":     row["Book-Author"],
            "image":      row.get("Image-URL-M", ""),
            "preview":    preview,
            "similarity": round(float(score), 4),
        })

    return recommended


# ──────────────────────────────────────────────────────────────
# Cached Google Books metadata  (TTL = 1 h per title)
# ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_book_metadata(title: str) -> dict:
    """Fetch and cache Google Books metadata for a single title."""
    return get_new_books(title)


# ──────────────────────────────────────────────────────────────
# Helper: render a small API-status notice if needed
# ──────────────────────────────────────────────────────────────
def _api_notice(data: dict) -> None:
    msg = get_error_message(data)
    if msg:
        st.info(f"ℹ️ {msg} Local information is still available.", icon=None)


# ──────────────────────────────────────────────────────────────
# SIDEBAR
# ──────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        "<div style='text-align:center;padding-top:12px;'>"
        "<span style='font-size:2.5rem;'>📚</span>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<h2 style='text-align:center;font-family:Space Grotesk,sans-serif;"
        "background:linear-gradient(135deg,#8b5cf6,#06b6d4);"
        "-webkit-background-clip:text;-webkit-text-fill-color:transparent;"
        "background-clip:text;margin:8px 0 4px;font-size:1.3rem;'>"
        "BookAI</h2>",
        unsafe_allow_html=True,
    )
    st.caption("AI-Powered Book Discovery")

    st.divider()

    # Dataset stats
    total_books   = books_df.shape[0]
    total_authors = books_df["Book-Author"].nunique()
    rec_books     = len(pt.index)

    st.markdown("**📊 Dataset**")
    st.markdown(f"- 📚 Catalog: **{total_books:,}** books")
    st.markdown(f"- ✍️ Authors: **{total_authors:,}** unique")
    st.markdown(f"- 🤖 Rec. model: **{rec_books:,}** books")

    st.divider()

    st.markdown("**🛠 Stack**")
    st.markdown(
        "- 🐍 Python · Streamlit\n"
        "- 📐 Collaborative Filtering\n"
        "- 📏 Cosine Similarity\n"
        "- 📚 Google Books API\n"
        "- 🗂 Pandas · NumPy"
    )

    st.divider()
    st.markdown(
        "<p style='font-size:0.78rem;color:#475569;text-align:center;'>"
        "Developed by <strong style='color:#8b5cf6;'>Teja &amp; Sandhu</strong><br>"
        "v2.0 — Collaborative Filtering</p>",
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════
# MAIN CONTENT
# ══════════════════════════════════════════════════════════════

# ── Hero ──────────────────────────────────────────────────────
st.markdown(
    """
    <div class="hero fade-in">
        <h1>Discover Your Next Favourite Book</h1>
        <p>
            Select a book you love and our engine surfaces the five
            most similar titles — powered by real reader ratings from
            over a million data points.
        </p>
        <div class="hero-badge">
            ✦ Collaborative Filtering · Cosine Similarity
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Stats row ─────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4, gap="medium")
with c1:
    st.metric("📚 Books in Catalog", f"{total_books:,}")
with c2:
    st.metric("✍️ Unique Authors", f"{total_authors:,}")
with c3:
    st.metric("🤖 Books with AI Recs", f"{rec_books:,}")
with c4:
    st.metric("📊 Training Ratings", "1,149,780")

st.divider()

# ═══════════════════════════════════════════════════════════
# SECTION 1 — BOOK SELECTION + DETAILS + RECOMMENDATIONS
# ═══════════════════════════════════════════════════════════
st.markdown(
    "<div class='section-header'>"
    "<h2>🔍 Find & Get Recommendations</h2>"
    "<p>Choose a book from the model library, review its details, then get AI recommendations.</p>"
    "</div>",
    unsafe_allow_html=True,
)

# Book selection dropdown (2,444 books known to the model)
book_name = st.selectbox(
    "Select a book from the recommendation library",
    options=pt.index.values,
    help="This list contains books with ≥50 reader ratings — the model's known library.",
)

# ── Selected book detail card ──────────────────────────────
selected_row = books_df[books_df["Book-Title"] == book_name]
if selected_row.empty:
    # Fallback: use model books data
    selected_row = books_model[books_model["Book-Title"] == book_name]

if not selected_row.empty:
    selected_book = selected_row.iloc[0]
else:
    selected_book = None

if selected_book is not None:
    # Fetch Google Books metadata (cached per title)
    meta = fetch_book_metadata(selected_book["Book-Title"])

    # Extract fields with safe fallbacks
    gb_rating       = None
    gb_ratings_count = 0
    gb_publisher    = selected_book.get("Publisher", "Unknown")
    gb_description  = "No description available."

    if "items" in meta:
        try:
            info            = meta["items"][0]["volumeInfo"]
            gb_rating       = info.get("averageRating")
            gb_ratings_count = info.get("ratingsCount", 0)
            gb_publisher    = info.get("publisher", gb_publisher)
            gb_description  = info.get("description", gb_description)
        except (IndexError, KeyError, TypeError):
            pass

    # ── Render the card ──
    with st.container():
        left_col, right_col = st.columns([1, 3], gap="large")

        with left_col:
            img_url = selected_book.get("Image-URL-M", "")
            if img_url:
                st.image(img_url, width=210, caption=None)
            else:
                st.markdown(
                    "<div style='width:210px;height:280px;background:rgba(139,92,246,0.1);"
                    "border:1px solid rgba(139,92,246,0.2);border-radius:12px;"
                    "display:flex;align-items:center;justify-content:center;"
                    "color:#8b5cf6;font-size:3rem;'>📖</div>",
                    unsafe_allow_html=True,
                )

        with right_col:
            # Title
            st.markdown(
                f"<div class='book-title-main'>{selected_book['Book-Title']}</div>",
                unsafe_allow_html=True,
            )

            # Author
            st.markdown(
                f"<div class='book-meta-row'>👤 <strong>Author</strong>&nbsp; "
                f"{selected_book['Book-Author']}</div>",
                unsafe_allow_html=True,
            )

            # Year
            year = selected_book.get("Year-Of-Publication", "Unknown")
            st.markdown(
                f"<div class='book-meta-row'>📅 <strong>Published</strong>&nbsp; {year}</div>",
                unsafe_allow_html=True,
            )

            # Publisher
            st.markdown(
                f"<div class='book-meta-row'>🏢 <strong>Publisher</strong>&nbsp; {gb_publisher}</div>",
                unsafe_allow_html=True,
            )

            # Rating
            if gb_rating:
                st.markdown(
                    f"<div class='book-meta-row'>"
                    f"<span class='rating-badge'>⭐ {gb_rating}/5</span>"
                    f"<span style='color:#64748b;font-size:0.82rem;margin-left:8px;'>"
                    f"({gb_ratings_count:,} reviews on Google Books)</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    "<div class='book-meta-row' style='color:#475569;'>⭐ Rating not available on Google Books</div>",
                    unsafe_allow_html=True,
                )

            # Description
            desc_preview = gb_description[:280] + ("…" if len(gb_description) > 280 else "")
            st.markdown(
                f"<div class='book-description'>{desc_preview}</div>",
                unsafe_allow_html=True,
            )

            # API error notice if any
            _api_notice(meta)

# ── Recommendations CTA ────────────────────────────────────
st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)

if st.button("✦ Get AI Recommendations", use_container_width=True, type="primary"):
    with st.spinner("Finding similar books…"):
        recs = recommend(book_name)

    if not recs:
        st.markdown(
            "<div class='empty-state'>"
            "<div class='empty-state-icon'>🔍</div>"
            "<div class='empty-state-text'>"
            "No recommendations found for this book. "
            "Try another title from the library."
            "</div></div>",
            unsafe_allow_html=True,
        )
    else:
        st.success(f"Found {len(recs)} books similar to **{book_name}**")

        # Section header
        st.markdown(
            f"<div class='section-header' style='margin-top:28px;'>"
            f"<h2>✦ Recommended For You</h2>"
            f"<p>Because you selected: <em>{book_name}</em> — "
            f"based on collaborative reader similarity patterns.</p>"
            f"</div>",
            unsafe_allow_html=True,
        )

        rec_cols = st.columns(len(recs), gap="medium")
        for col, book in zip(rec_cols, recs):
            with col:
                with st.container(border=True):
                    # Cover
                    if book["image"]:
                        st.image(book["image"], use_container_width=True)
                    else:
                        st.markdown(
                            "<div style='aspect-ratio:2/3;background:rgba(139,92,246,0.08);"
                            "border-radius:10px;display:flex;align-items:center;"
                            "justify-content:center;font-size:2.5rem;'>📖</div>",
                            unsafe_allow_html=True,
                        )

                    # Title
                    st.markdown(
                        f"<div class='rec-card-title'>{book['title']}</div>",
                        unsafe_allow_html=True,
                    )

                    # Author
                    st.markdown(
                        f"<div class='rec-card-author'>✍️ {book['author']}</div>",
                        unsafe_allow_html=True,
                    )

                    # "Recommended match" label (no fabricated %)
                    st.markdown(
                        "<div class='rec-match-badge'>✦ Recommended Match</div>",
                        unsafe_allow_html=True,
                    )

                    # Preview link
                    if book["preview"]:
                        st.link_button(
                            "📖 Read Preview",
                            book["preview"],
                            use_container_width=True,
                        )


# ═══════════════════════════════════════════════════════════
# SECTION 2 — SEARCH
# ═══════════════════════════════════════════════════════════
st.divider()

st.markdown(
    "<div class='section-header'>"
    "<h2>🔎 Search the Library</h2>"
    "<p>Search by title across the full 271K-book catalog and Google Books.</p>"
    "</div>",
    unsafe_allow_html=True,
)

search_query = st.text_input(
    "Search for a book",
    placeholder="e.g. Harry Potter, Dune, The Alchemist…",
    label_visibility="collapsed",
)

if search_query and search_query.strip():
    sq = search_query.strip()

    # ── Local catalog results ──────────────────────────────
    st.markdown(
        "<span class='search-source-label label-local'>📂 Local Library Results</span>",
        unsafe_allow_html=True,
    )

    local_matches = books_df[
        books_df["Book-Title"].str.contains(sq, case=False, na=False, regex=False)
        | books_df["Book-Author"].str.contains(sq, case=False, na=False, regex=False)
    ].drop_duplicates("Book-Title").head(6)

    if local_matches.empty:
        st.markdown(
            "<div class='empty-state'>"
            "<div class='empty-state-icon'>📂</div>"
            "<div class='empty-state-text'>No matches found in local catalog for <em>"
            + sq + "</em>.</div></div>",
            unsafe_allow_html=True,
        )
    else:
        for _, row in local_matches.iterrows():
            with st.container(border=True):
                lcol, rcol = st.columns([1, 5], gap="medium")
                with lcol:
                    img = row.get("Image-URL-M", "")
                    if img:
                        st.image(img, width=70)
                    else:
                        st.markdown(
                            "<div style='width:70px;height:90px;background:"
                            "rgba(139,92,246,0.1);border-radius:8px;display:flex;"
                            "align-items:center;justify-content:center;font-size:1.5rem;'>"
                            "📖</div>",
                            unsafe_allow_html=True,
                        )
                with rcol:
                    st.markdown(f"**{row['Book-Title']}**")
                    st.caption(
                        f"👤 {row['Book-Author']} · "
                        f"📅 {row.get('Year-Of-Publication','?')} · "
                        f"🏢 {row.get('Publisher','?')}"
                    )

    # ── Google Books results ───────────────────────────────
    st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
    st.markdown(
        "<span class='search-source-label label-google'>🌐 Google Books Results</span>",
        unsafe_allow_html=True,
    )

    with st.spinner("Fetching from Google Books…"):
        gb_data = get_new_books(sq)

    api_err = get_error_message(gb_data)
    if api_err:
        st.info(f"ℹ️ {api_err}")
    elif "items" not in gb_data:
        st.markdown(
            "<div class='empty-state'>"
            "<div class='empty-state-icon'>🌐</div>"
            "<div class='empty-state-text'>No results from Google Books for <em>"
            + sq + "</em>.</div></div>",
            unsafe_allow_html=True,
        )
    else:
        for item in gb_data["items"][:5]:
            try:
                info        = item.get("volumeInfo", {})
                title       = info.get("title", "Unknown Title")
                authors     = ", ".join(info.get("authors", ["Unknown Author"]))
                thumbnail   = info.get("imageLinks", {}).get("thumbnail", "")
                rating_v    = info.get("averageRating", "")
                published   = info.get("publishedDate", "Unknown")
                categories  = ", ".join(info.get("categories", ["Unknown"]))
                description = info.get("description", "No description available.")
                preview     = info.get("previewLink", "")

                with st.container(border=True):
                    g1, g2 = st.columns([1, 5], gap="medium")
                    with g1:
                        if thumbnail:
                            st.image(thumbnail, width=70)
                        else:
                            st.markdown(
                                "<div style='width:70px;height:90px;background:"
                                "rgba(6,182,212,0.08);border-radius:8px;display:flex;"
                                "align-items:center;justify-content:center;font-size:1.5rem;'>"
                                "📖</div>",
                                unsafe_allow_html=True,
                            )
                    with g2:
                        st.markdown(f"**{title}**")
                        meta_parts = [f"👤 {authors}", f"📅 {published}"]
                        if rating_v:
                            meta_parts.append(f"⭐ {rating_v}")
                        if categories != "Unknown":
                            meta_parts.append(f"🏷️ {categories}")
                        st.caption(" · ".join(meta_parts))
                        st.markdown(
                            f"<div style='font-size:0.85rem;color:#94a3b8;margin-top:4px;'>"
                            f"{description[:300]}{'…' if len(description) > 300 else ''}"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                        if preview:
                            st.link_button("📖 Read Preview", preview)
            except (KeyError, TypeError, IndexError):
                continue  # skip malformed items silently


# ═══════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════
st.markdown(
    "<div class='footer'>"
    "Built by <span>Teja &amp; Sandhu</span> · "
    "Collaborative Filtering on the Book-Crossings Dataset · "
    "Enriched with Google Books API"
    "</div>",
    unsafe_allow_html=True,
)
