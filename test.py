"""
test.py -- Comprehensive unit and smoke tests for BookRecommendationApp

Run with:
    python test.py

These tests do NOT require a running Streamlit server or a live network connection.
"""

import os
import sys
import pickle
import numpy as np
import pandas as pd

# -- ensure project root is on the path
sys.path.insert(0, os.path.dirname(__file__))

# -- patch st.secrets before importing google_books
# google_books.py calls st.secrets["KEY"]; we mock it to raise KeyError
# so _get_api_key() falls through to os.environ (also unset) -> returns None.
import streamlit as st

class _MockSecrets:
    """Raise KeyError on any key access to simulate missing secrets."""
    def __getitem__(self, key):
        raise KeyError(key)
    def get(self, key, default=None):
        return default

st.secrets = _MockSecrets()  # type: ignore

from google_books import get_new_books, get_error_message, _get_api_key

# ------------------------------------------------------------
PASS = "[PASS]"
FAIL = "[FAIL]"

results = []


def check(name, condition, note=""):
    results.append((name, condition, note))
    status = PASS if condition else FAIL
    msg = f"  {status}  {name}"
    if note:
        msg += f" -- {note}"
    print(msg)


# ============================================================
# 1. Google Books helper -- Security & Error paths
# ============================================================
print("\n-- google_books.py (Security & Error Handling) ----------")

# When no API key is available the function must return a dict, not raise.
result_no_key = get_new_books("Harry Potter")
check(
    "get_new_books returns dict on missing key",
    isinstance(result_no_key, dict),
    f"got {type(result_no_key).__name__}",
)

# get_error_message must return a string for the no_api_key error
err_msg = get_error_message({"_error": "no_api_key"})
check(
    "get_error_message returns string for no_api_key",
    isinstance(err_msg, str) and len(err_msg) > 0,
    repr(err_msg),
)

# get_error_message must return None when there is no error
ok_msg = get_error_message({"items": []})
check(
    "get_error_message returns None for clean dict",
    ok_msg is None,
    repr(ok_msg),
)

# Empty query should return an empty dict gracefully
empty_q = get_new_books("   ")
check(
    "get_new_books handles empty/whitespace query",
    isinstance(empty_q, dict),
)

# get_error_message handles unknown _error values without raising
weird = get_error_message({"_error": "some_new_error_code"})
check(
    "get_error_message handles unknown error codes",
    isinstance(weird, str),
    repr(weird),
)


# ============================================================
# 2. Model files presence & structure
# ============================================================
print("\n-- model files -----------------------------------------")

MODEL_FILES = [
    "model/pt.pkl",
    "model/books.pkl",
    "model/similarity_scores.pkl",
]

for fpath in MODEL_FILES:
    check(f"File exists: {fpath}", os.path.isfile(fpath))

all_present = all(os.path.isfile(f) for f in MODEL_FILES)
if all_present:
    pt          = pickle.load(open("model/pt.pkl",                "rb"))
    books_model = pickle.load(open("model/books.pkl",             "rb"))
    sim_scores  = pickle.load(open("model/similarity_scores.pkl", "rb"))

    check("pt is a pandas DataFrame",    isinstance(pt, pd.DataFrame))
    check("books_model is a DataFrame",  isinstance(books_model, pd.DataFrame))
    check("sim_scores is a numpy array", isinstance(sim_scores, np.ndarray))

    n = len(pt.index)
    check("sim_scores shape matches pt", sim_scores.shape == (n, n),
          f"pt={n}, sim={sim_scores.shape}")

    check("pt has at least 1 book",               n > 0)
    check("books_model has Book-Title column",    "Book-Title"   in books_model.columns)
    check("books_model has Image-URL-M column",   "Image-URL-M"  in books_model.columns)
else:
    print("  [!]  Model files missing -- skipping structural checks.")


# ============================================================
# 3. Books.csv presence & structure
# ============================================================
print("\n-- Books.csv -------------------------------------------")

if os.path.isfile("Books.csv"):
    books_df = pd.read_csv("Books.csv", nrows=10, low_memory=False)
    required_cols = ["Book-Title", "Book-Author",
                     "Year-Of-Publication", "Publisher", "Image-URL-M"]
    for col in required_cols:
        check(f"Books.csv has column '{col}'", col in books_df.columns)
else:
    print("  [!]  Books.csv not found -- skipping.")


# ============================================================
# 4. Recommendation algorithm correctness & properties
# ============================================================
print("\n-- recommendation logic ---------------------------------")

if all_present:
    first_book = pt.index[0]

    matches = np.where(pt.index == first_book)[0]
    check(
        "np.where finds known book",
        len(matches) > 0,
        f"book='{first_book}'",
    )

    if len(matches) > 0:
        idx = matches[0]
        similar = sorted(
            list(enumerate(sim_scores[idx])),
            key=lambda x: x[1],
            reverse=True,
        )[1:6]
        check(
            "Returns up to 5 similar items",
            1 <= len(similar) <= 5,
            f"got {len(similar)}",
        )
        check(
            "All similarity scores are floats in [0, 1]",
            all(0.0 <= s <= 1.0 for _, s in similar),
        )
        check(
            "Similarity scores are in descending order",
            [s for _, s in similar] == sorted([s for _, s in similar], reverse=True),
        )

    # Self-exclusion check: recommended books must NEVER include the selected book
    test_sample = [pt.index[i] for i in [0, min(10, len(pt.index)-1), min(50, len(pt.index)-1)]]
    all_self_excluded = True
    all_deterministic = True
    for test_b in test_sample:
        m = np.where(pt.index == test_b)[0][0]
        rec_indices = [idx for idx, _ in sorted(enumerate(sim_scores[m]), key=lambda x: x[1], reverse=True)[1:6]]
        rec_titles = [pt.index[i] for i in rec_indices]
        if test_b in rec_titles:
            all_self_excluded = False
        # Determinism check
        rec_indices2 = [idx for idx, _ in sorted(enumerate(sim_scores[m]), key=lambda x: x[1], reverse=True)[1:6]]
        if rec_indices != rec_indices2:
            all_deterministic = False

    check("Recommendations strictly exclude selected book (no self-matches)", all_self_excluded)
    check("Recommendations are fully deterministic", all_deterministic)

    bad_matches = np.where(pt.index == "BOOK_THAT_DOES_NOT_EXIST_XYZ")[0]
    check(
        "np.where returns empty array for unknown book",
        len(bad_matches) == 0,
    )
else:
    print("  [!]  Model files missing -- skipping recommendation tests.")


# ============================================================
# 5. Search Engine correctness & edge cases
# ============================================================
print("\n-- search engine ---------------------------------------")

if os.path.isfile("Books.csv"):
    books_full = pd.read_csv("Books.csv", nrows=1000, low_memory=False)
    
    def search_local(query, df):
        q = str(query).strip()
        if not q:
            return pd.DataFrame()
        mask = (
            df["Book-Title"].str.contains(q, case=False, na=False, regex=False)
            | df["Book-Author"].str.contains(q, case=False, na=False, regex=False)
        )
        return df[mask].drop_duplicates("Book-Title").head(6)

    # Regex special characters must NOT raise errors
    special_queries = ["???", "C++", "[Guide]", "Book (Vol 1)", "King*", "Author$"]
    no_crash_special = True
    for sq in special_queries:
        try:
            search_local(sq, books_full)
        except Exception:
            no_crash_special = False
            break
    check("Search handles regex special characters safely (regex=False)", no_crash_special)

    # Empty search returns empty DataFrame
    empty_search_res = search_local("", books_full)
    check("Empty search returns empty result", empty_search_res.empty)

    # Case insensitive search
    sample_title = books_full["Book-Title"].dropna().iloc[0]
    res_lower = search_local(sample_title.lower(), books_full)
    res_upper = search_local(sample_title.upper(), books_full)
    check(
        "Search is case-insensitive",
        len(res_lower) > 0 and len(res_upper) > 0,
    )


# ============================================================
# Summary
# ============================================================
print("\n" + "-" * 54)
passed = sum(1 for _, ok, _ in results if ok)
total  = len(results)
print(f"Results: {passed}/{total} passed\n")

if passed < total:
    sys.exit(1)