from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import pandas as pd

# Example user metadata dataset
user_data = pd.read_csv('./datasets/user_metadata.csv')

# Filter users with no ratings
ratings = pd.read_csv('./datasets/ratings.csv')
rated_users = ratings['userId'].unique()
cold_start_users = user_data[~user_data['userId'].isin(rated_users)]

# Select features for clustering (e.g., age, location, job, interests)
features = cold_start_users[['age_group', 'location', 'job']]

# Encode categorical data
features = pd.get_dummies(features, drop_first=True)

# Scale features
scaler = StandardScaler()
scaled_features = scaler.fit_transform(features)

# Apply KMeans
kmeans = KMeans(n_clusters=5, random_state=42)
cold_start_users['cluster'] = kmeans.fit_predict(scaled_features)

# Output user clusters
print(cold_start_users[['userId', 'cluster']])

cold_start_users.to_csv('./datasets/user_metadata.csv', index=False)