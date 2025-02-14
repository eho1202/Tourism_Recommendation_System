import numpy as np
import pandas as pd
from surprise import Reader, Dataset, KNNBasic, accuracy
from surprise.model_selection import KFold

ratings = pd.read_csv('./datasets/ratings.csv')

# Define the reader object with no rating scale specified (auto-detected)
reader = Reader()

# Load data into Surprise Dataset
data = Dataset.load_from_df(ratings[['userId', 'itemId', 'rating']], reader)

# Use K-Fold cross-validation
kf = KFold(n_splits=5)

# Use KNNBasic algorithm for item-based collaborative filtering
sim_options = {
    'name': 'cosine',
    'user_based': False  # Item-based collaborative filtering
}
algo = KNNBasic(sim_options=sim_options)

# Train and evaluate the model
for trainset, testset in kf.split(data):
    algo.fit(trainset)
    predictions = algo.test(testset)
    accuracy.rmse(predictions, verbose=True)
    accuracy.mae(predictions, verbose=True)

# Build the full trainset and train the algorithm
trainset = data.build_full_trainset()
algo.fit(trainset)

def get_item_recommendations(item_id, n=5):
    inner_id = algo.trainset.to_inner_iid(item_id)
    neighbors = algo.get_neighbors(inner_id, k=n)
    item_recommendations = [algo.trainset.to_raw_iid(inner_id) for inner_id in neighbors]
    return item_recommendations

# item_id = 8  # Replace with an actual item ID
# recommendations = get_item_recommendations(item_id, 5)
# print("Top 5 item-based recommendations for item", item_id, ":")
# print(recommendations)

