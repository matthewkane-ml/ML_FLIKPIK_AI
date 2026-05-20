"""
Train and save the FlikPik hybrid recommender model.

Run from the project root:
    python src/train_model.py

This creates the model file used by the app:
    models/hybrid_recommender.pkl

Keep this script in the repository and regenerate the model when needed.
It is also called automatically during the Render build step.
"""

import os
import pickle
import sys
from pathlib import Path

# Make sure src imports work whether this file is run from the root or src folder.
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from config import MODEL_PATH, RECOMMENDER_PARAMS
from data_loader import load_processed_data
from recommender import HybridRecommender


def train_and_save_model():
    """Load processed data, train the recommender, and save it as .pkl."""
    print("Loading processed data...")
    train, val, test, movies, genres = load_processed_data()

    print(f"Training rows: {len(train):,}")
    print(f"Movies: {len(movies):,}")

    model = HybridRecommender(
        train_df=train,
        movies_df=movies,
        genre_df=genres,
        **RECOMMENDER_PARAMS,
    )

    print("Training hybrid recommender...")
    model.fit()

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f, protocol=pickle.HIGHEST_PROTOCOL)

    print("Model training complete.")
    print(f"Saved model: {MODEL_PATH}")
    return model


if __name__ == "__main__":
    train_and_save_model()
