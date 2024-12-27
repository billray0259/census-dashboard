from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
import numpy as np
import os

from pymongo import MongoClient

def get_utm_epsg(lat, lon):
    """Return the EPSG code for the UTM zone corresponding to lat/lon."""
    zone = int((lon + 180) // 6) + 1
    if lat >= 0:
        epsg = 32600 + zone  # Northern Hemisphere
    else:
        epsg = 32700 + zone  # Southern Hemisphere
    return epsg

def embed(texts):
    ai_client = OpenAI()
    response = ai_client.embeddings.create(
        input=texts,
        model="text-embedding-3-small"
    )
    return np.array([d.embedding for d in response.data])


def find_intersecting_features(database_name, collection_name, geojson):
    """
    Find all documents in a collection that intersect with a given GeoJSON object.
    
    :param database_name: Name of the database
    :param collection_name: Name of the collection
    :param geojson: A GeoJSON object to check intersection with
    :param mongo_uri: MongoDB connection URI (defaults to localhost if not provided)
    :return: A list of documents that intersect with the given GeoJSON
    """
    client = MongoClient(os.getenv('MONGODB_URI'))
    db = client[database_name]
    collection = db[collection_name]
    
    # Perform the geospatial query using $geoIntersects
    intersecting_documents = collection.find(
        {
            "geometry": {
                "$geoIntersects": {
                    "$geometry": geojson
                }
            }
        }
    )
    # Collect intersecting results
    results = list(intersecting_documents)
    
    return results


def semantic_search_2023_tables(query, k=10):
    # Connect to MongoDB Atlas
    client = MongoClient(os.getenv('ATLAS_URI'))
    db = client['census-dashboard']
    collection = db['2023-tables']

    # Compute the query embedding
    query_embedding = embed(query)[0].tolist()  # Replace with your embedding function

    # Perform the vector search
    # return name description variables universe
    pipeline = [
        {
            '$vectorSearch': {
                'index': 'default',
                'path': 'embedding',
                'queryVector': query_embedding,
                'numCandidates': 150,
                'limit': k
            }
        },
        {
            '$project': {
                'name': 1,
                'description': 1,
                'variables': 1,
                'universe': 1,
                'score': {'$meta': 'searchScore'}
            }
        }
    ]

    results = list(collection.aggregate(pipeline))
    return results