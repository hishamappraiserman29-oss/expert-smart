import json
import os
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def run():
    print("--- 1. Loading embedding model... ---")
    model = SentenceTransformer('intfloat/multilingual-e5-large')

    print("--- 2. Loading market data... ---")
    data_path = os.path.join(BASE_DIR, 'data_lake', 'market_data.json')
    with open(data_path, 'r', encoding='utf-8') as f:
        listings = json.load(f)

    print("--- 3. Connecting to Qdrant... ---")
    client = QdrantClient(path=os.path.join(BASE_DIR, 'vector_db'))

    # Recreate collection from scratch
    try:
        client.delete_collection('egypt_estate')
    except Exception:
        pass
    client.create_collection(
        collection_name='egypt_estate',
        vectors_config=VectorParams(size=1024, distance=Distance.COSINE)
    )

    print(f"--- 4. Embedding {len(listings)} listings... ---")
    points = []
    for i, listing in enumerate(listings):
        text = (
            f"passage: شقة في {listing['loc']} "
            f"بسعر {listing['pr']} جنيه "
            f"ومساحة {listing['ar']} متر مربع"
        )
        vector = model.encode(text).tolist()
        points.append(PointStruct(id=i, vector=vector, payload=listing))

    client.upsert(collection_name='egypt_estate', points=points)
    print(f"--- Done! {len(points)} listings stored. ---")

if __name__ == '__main__':
    run()
