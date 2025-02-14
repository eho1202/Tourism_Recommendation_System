import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

tourism_data = pd.read_csv('datasets/tourist_destinations.csv')

# Combine relevant textual features
tourism_data['content'] = tourism_data['description'] + ' ' + tourism_data['category'] + ' ' + tourism_data['country']

# TF-IDF Vectorization
tfidf = TfidfVectorizer(stop_words='english')
tfidf_matrix = tfidf.fit_transform(tourism_data['content'])

# Cosine similarity
cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)

def get_content_recommendations(item_id, n=5):
    idx = tourism_data[tourism_data['itemId'] == item_id].index[0]
    sim_scores = list(enumerate(cosine_sim[idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
    sim_scores = sim_scores[1:n+1]
    item_indices = [i[0] for i in sim_scores]
    return tourism_data.iloc[item_indices]

# item_id = 3  # Replace with an actual item ID
# recommendations = get_content_recommendations(item_id, 5)
# print("Top 5 content-based recommendations for item", item_id, ":")
# print(recommendations[['itemId', 'name', 'description']])