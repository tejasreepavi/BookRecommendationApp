# 📚 BookRecommendationApp

> An AI-powered book recommendation system using collaborative filtering (KNN / Cosine Similarity) enriched with real-time metadata from the Google Books API.

---

## 🌟 Overview

BookRecommendationApp is a **Streamlit web application** that recommends books to users based on collaborative reader patterns. It uses a pre-trained collaborative filtering model built on the [Book-Crossings dataset](http://www2.informatik.uni-freiburg.de/~cziegler/BX/) (271,360 books, 1,149,780 ratings, 278,859 users), augmented with live book metadata (ratings, descriptions, preview links) from the **Google Books API**.

### Key Workflow

1. **Explore Library**: User selects a book from a curated library of **2,444 popular books** (books with ≥50 ratings in the training set).
2. **Rich Details**: The application displays the selected book's cover, author, year, publisher, and live Google Books metadata (rating, review count, description).
3. **AI Recommendations**: Clicking **"✦ Get AI Recommendations"** returns **5 similar books** using cosine similarity on the user-rating matrix.
4. **Preview & Discovery**: Each recommended book card displays its cover, title, author, match badge, and a direct "Read Preview" link to Google Books.
5. **Dual Search**: Search the local 271K-book catalog and Google Books API simultaneously with instant results.

---

## ✨ Features

- 🤖 **AI Book Recommendations** — collaborative filtering (cosine similarity) on 1.1M real user ratings.
- 🎨 **Modern Glassmorphism UI** — custom dark theme with Space Grotesk + Inter typography, purple-to-cyan glow accents, responsive cards, and clean visual hierarchy.
- ⚡ **High-Performance Caching** — `@st.cache_resource` for model matrices and `@st.cache_data` (TTL=1h) for API calls, eliminating redundant disk I/O and network latency.
- 🔒 **Enterprise-Grade Security** — zero hardcoded API keys; loads securely from `.streamlit/secrets.toml` with `.gitignore` protection and `.example` template.
- 🛡️ **Graceful Fault Tolerance** — comprehensive try/except handling with user-friendly notices; the app never crashes if the network or API fails.
- 🌐 **Google Books Enrichment** — live metadata (ratings, review counts, descriptions, categories, preview links).
- 🔎 **Dual Search Engine** — simultaneously queries the local dataset and the Google Books API.
- 📊 **Dataset Metrics** — real-time statistics on total books, authors, and AI model library size.
- 🧪 **Automated Test Suite** — 24 passing unit and smoke tests in `test.py`.

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| **Web Framework** | [Streamlit](https://streamlit.io/) >= 1.58.0 |
| **Language** | Python 3.10+ (tested on Python 3.14) |
| **Data Processing** | Pandas >= 3.0.0 |
| **Numerical Computing** | NumPy >= 2.0.0 |
| **ML Algorithm** | Cosine Similarity (scikit-learn >= 1.4.0) |
| **Model Serialization** | Python `pickle` |
| **External API** | [Google Books API v1](https://developers.google.com/books/docs/v1/using) |
| **HTTP Client** | `requests` >= 2.32.0 |
| **Styling** | Modern Glassmorphism CSS (`assets/style.css`) |
| **Dataset** | [Book-Crossings](http://www2.informatik.uni-freiburg.de/~cziegler/BX/) |

---

## 📐 Architecture

```
User (Browser)
     │
     ▼
Streamlit App (app.py)
     │
     ├── [Startup: @st.cache_resource]
     │     ├── Load model/pt.pkl                (Pivot table: 2,444 books × 47,994 users)
     │     ├── Load model/books.pkl             (Books DataFrame: 271,360 records)
     │     └── Load model/similarity_scores.pkl (2,444 × 2,444 cosine similarity matrix)
     │
     ├── [Startup: @st.cache_data]
     │     └── Load Books.csv                   (Full book catalog)
     │
     ├── [On Book Selection: @st.cache_data(ttl=3600)]
     │     └── google_books.py ──► Google Books API (Rating, description, preview)
     │
     ├── [On "Get Recommendations"]
     │     └── recommend(book_name):
     │           ├── Lookup book index in pivot table
     │           ├── Retrieve row from similarity_scores matrix
     │           ├── Sort top 5 similar items (excluding self)
     │           └── Fetch preview links from Google Books API
     │
     └── [On Search Query]
           ├── Filter local Books.csv (regex/substring match)
           └── Query Google Books API for live external results
```

---

## 📁 Project Structure

```
BookRecommendationApp/
├── app.py                         # Main Streamlit web application
├── google_books.py                # Secure Google Books API client
├── recommendation.py              # Offline model training & matrix generation script
├── test.py                        # Automated test suite (24 passing tests)
├── requirements.txt               # Python package dependencies
├── .gitignore                     # Git rules (protects secrets.toml, caches, virtualenvs)
├── .streamlit/
│   ├── secrets.toml               # Local API secrets (DO NOT COMMIT)
│   └── secrets.toml.example       # Template for API secrets
├── assets/
│   └── style.css                  # Glassmorphism dark-theme design system
├── model/
│   ├── pt.pkl                     # Pre-computed pivot table (~938 MB)
│   ├── books.pkl                  # Books DataFrame pickle (~86 MB)
│   └── similarity_scores.pkl      # Cosine similarity matrix (~48 MB)
├── Books.csv                      # Book catalog — 271,360 books (~73 MB)
├── Ratings.csv                    # User ratings — 1,149,780 ratings (~22 MB)
├── Users.csv                      # User demographics — 278,859 users (~11 MB)
├── PROJECT_ANALYSIS.md            # In-depth architectural and technical audit report
├── PHASE_3_AUDIT.md               # Pre-GitHub security & quality audit report
└── PHASE_4_GITHUB_READINESS.md    # GitHub readiness and staging evaluation
```

---

## 📦 Git LFS (Large File Storage)

The pre-computed recommendation model files (`model/*.pkl`) exceed standard GitHub file-size limits (specifically `model/pt.pkl` at ~938 MB). If cloning or pushing with full model weights:

1. Install Git LFS: [git-lfs.com](https://git-lfs.com/)
2. Initialize LFS: `git lfs install`
3. Pull model files: `git lfs pull`

> 💡 **Alternative (No Git LFS):** You can also clone without LFS and generate the model files locally by running `python recommendation.py`.

---

## 🚀 Installation & Setup

### Prerequisites

- Python 3.10+
- Git & Git LFS (optional, see above)
- ~2 GB free disk space (for model files and dataset CSVs)
- Google Books API key ([Google Cloud Console](https://console.cloud.google.com/))

### 1. Clone the repository

```bash
git clone <repository-url>
cd BookRecommendationApp
```

### 2. Set up virtual environment

```bash
# Create virtual environment
python -m venv venv

# Activate on Windows (PowerShell / CMD)
venv\Scripts\activate

# Activate on macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure API Secrets

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and add your Google Books API key:

```toml
# .streamlit/secrets.toml
GOOGLE_BOOKS_API_KEY = "your-google-books-api-key-here"
```

> 💡 *Note:* If no API key is provided, the app continues to function with full local recommendations, dataset metadata, and offline covers, displaying a gentle informational notice.

---

## 💻 Running the Application

### Start Streamlit

```bash
streamlit run app.py

# Or if streamlit is not on your global PATH:
python -m streamlit run app.py
```

Open your browser and navigate to `http://localhost:8501`.

---

## 🧪 Running Tests

To run the automated smoke and unit test suite:

```bash
python test.py
```

This tests:
- `google_books.py` error handling, edge cases, and missing keys
- Model pickle files integrity and matrix dimensions
- `Books.csv` schema validation
- Collaborative filtering recommendation algorithm logic and outputs

---

## 🧠 Recommendation Model & Training

**Algorithm:** Collaborative Filtering using Cosine Similarity on User-Item Matrix.

- **Training data:** 1,149,780 user-book ratings from the Book-Crossings dataset.
- **Filtering:** High-confidence threshold (books with ≥50 ratings).
- **Matrix:** 2,444 books × 47,994 users sparse pivot table.
- **Similarity:** Pre-computed 2,444 × 2,444 cosine similarity matrix.

To re-train the model or regenerate pickle files:

```bash
python recommendation.py
```

---

## 🔒 Security & Privacy

- **No Hardcoded Keys:** All external API secrets are managed through `st.secrets` or environment variables.
- **Git Protection:** `.streamlit/secrets.toml` is strictly ignored by `.gitignore`.
- **Safe Rendering:** HTML injection points are sanitized and styled via static CSS classes.

---

## 👥 Credits

Developed by **Teja & Sandhu**  
Modernized with AI-powered discovery, secure API infrastructure, and glassmorphism styling.
