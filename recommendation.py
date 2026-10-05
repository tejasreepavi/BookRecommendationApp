import pandas as pd
import pickle
from sklearn.metrics.pairwise import cosine_similarity

# Load datasets
books = pd.read_csv("Books.csv")
ratings = pd.read_csv("Ratings.csv")

# Merge books and ratings
merged = ratings.merge(books, on="ISBN")

# Keep books with at least 50 ratings
rating_count = merged.groupby("Book-Title").count()["Book-Rating"].reset_index()
rating_count.rename(columns={"Book-Rating": "num_ratings"}, inplace=True)

popular_books = rating_count[rating_count["num_ratings"] >= 50]

merged = merged.merge(popular_books, on="Book-Title")

# Create pivot table
pt = merged.pivot_table(
    index="Book-Title",
    columns="User-ID",
    values="Book-Rating"
)

pt.fillna(0, inplace=True)

# Calculate similarity
similarity_scores = cosine_similarity(pt)

# Save model files
pickle.dump(pt, open("model/pt.pkl", "wb"))
pickle.dump(similarity_scores, open("model/similarity_scores.pkl", "wb"))
pickle.dump(books, open("model/books.pkl", "wb"))

print("Model files created successfully!")