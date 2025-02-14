import pandas as pd
from surprise import SVD, Dataset, Reader, KNNBasic, accuracy
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from surprise.model_selection import KFold

from collaborative_filter import get_item_recommendations
from content_based_filter import get_content_recommendations

# Load data
tourism_data = pd.read_csv('./datasets/tourist_destinations.csv')
ratings = pd.read_csv('./datasets/ratings.csv')
user_metadata = pd.read_csv('./datasets/user_metadata.csv')

# Content-based filtering
tourism_data['content'] = tourism_data['description'] + ' ' + tourism_data['category']
tfidf = TfidfVectorizer(stop_words='english')
tfidf_matrix = tfidf.fit_transform(tourism_data['content'])
cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)

# Collaborative filtering
reader = Reader(rating_scale=(1, 5))
data = Dataset.load_from_df(ratings[['userId', 'itemId', 'rating']], reader)
trainset = data.build_full_trainset()
svd = SVD()
svd.fit(trainset)

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

item_indices = pd.Series(tourism_data.index, index=tourism_data['name']).drop_duplicates()

def hybrid_recommender(userId, item_name=None, n=5):
    user_ratings_count = len(ratings[ratings['userId'] == userId])

    if userId not in ratings['userId'].unique():
        # New user - use clustering
        user_cluster = user_metadata[user_metadata['userId'] == userId]['cluster'].values[0]
        cluster_users = user_metadata[user_metadata['cluster'] == user_cluster]['userId'].values
        cluster_ratings = ratings[ratings['userId'].isin(cluster_users)]
        
        # Get top-rated items from the cluster
        top_items = cluster_ratings.groupby('itemId')['rating'].mean().sort_values(ascending=False).head(n)
        return tourism_data[tourism_data['itemId'].isin(top_items.index)]['name'].values

    elif user_ratings_count > 15:
        # Item-based collaborative filtering
        if item_name:
            item_id = tourism_data.loc[tourism_data['name'] == item_name, 'itemId'].values[0]
            recommendations = get_item_recommendations(item_id, n)
            return tourism_data[tourism_data['itemId'].isin(recommendations)]['name'].tolist()
        else:
            # Recommend top-rated items for the user based on collaborative filter
            user_items = ratings[ratings['userId'] == userId]['itemId']
            all_items = tourism_data[~tourism_data['itemId'].isin(user_items)]
            all_items['est'] = all_items['itemId'].apply(lambda x: algo.predict(userId, x).est)
            return all_items.sort_values('est', ascending=False).head(n)['name'].tolist()

    else:
        # Content-based filtering
        if item_name:
            item_id = tourism_data.loc[tourism_data['name'] == item_name, 'itemId'].values[0]
            recommendations = get_content_recommendations(item_id, n)
            return recommendations['name'].tolist()
        else:
            # Recommend top-rated items based on content similarity
            return tourism_data.sort_values('rating', ascending=False).head(n)['name'].tolist()

# Example usage
print("Recommendations for userId=45:",hybrid_recommender(45, 'Eiffel Tower', 5)) # Should use cb
print("Recommendations for userId=59:", hybrid_recommender(userId=59, n=5)) # Should use cf
print("Recommendations for userId=199",hybrid_recommender(userId=199, n=5)) # Should cluster first then cb