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
    print('Connected to MongoDB')
    
    # Perform the geospatial query using $geoIntersects
    try:
        intersecting_documents = collection.find(
            {
                "geometry": {
                    "$geoIntersects": {
                        "$geometry": geojson
                    }
                },
                "properties.GEOID": "08"  # Add this condition to filter by GEOID
            }, {
                "_id": 1,
                "properties": 1
            }
        )
        # combine into one dict
        intersecting_documents = [{'_id': doc['_id'], **doc['properties']} for doc in intersecting_documents]
    except Exception as e:
        print(str(e)[:1000])
        return None
    
    # # Collect intersecting results
    results = list(intersecting_documents)
    
    return results