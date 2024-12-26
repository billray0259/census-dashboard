import os
import sys
import json
from dotenv import load_dotenv
load_dotenv()
import shapefile  # pyshp library
from pymongo import MongoClient

def convert_shp_to_geojson(shp_file_path):
    """Convert a shapefile (.shp) to GeoJSON."""
    with shapefile.Reader(shp_file_path) as shp:
        fields = shp.fields[1:]  # First field is a delete flag
        field_names = [field[0] for field in fields]
        
        geojson_features = []
        for sr in shp.shapeRecords():
            attributes = sr.record.as_dict()
            geom = sr.shape.__geo_interface__
            feature = {
                "type": "Feature",
                "geometry": geom,
                "properties": {name: attributes[name] for name in field_names}
            }
            geojson_features.append(feature)

    geojson = {
        "type": "FeatureCollection",
        "features": geojson_features
    }
    
    return geojson

def main():
    if len(sys.argv) != 4:
        print("Usage: python script.py <directory_path> <database_name> <collection_name>")
        sys.exit(1)
        
    directory_path = sys.argv[1]
    database_name = sys.argv[2]
    collection_name = sys.argv[3]

    # Load MongoDB connection string from an environment variable
    mongo_conn_str = os.getenv('MONGODB_URI')
    if not mongo_conn_str:
        print("Error: MONGODB_URI environment variable not set.")
        sys.exit(1)
    
    # Connect to MongoDB
    client = MongoClient(mongo_conn_str)
    db = client[database_name]
    collection = db[collection_name]

    # Iterate over all .shp files in the directory
    for filename in os.listdir(directory_path):
        if filename.endswith(".shp"):
            shapefile_path = os.path.join(directory_path, filename)
            # Convert the shapefile to GeoJSON
            print(shapefile_path)
            geojson_data = convert_shp_to_geojson(shapefile_path)
            # Insert GeoJSON features into the collection
            if geojson_data["features"]:
                collection.insert_many(geojson_data["features"])
                print(f"Inserted {len(geojson_data['features'])} features from {filename} into {database_name}.{collection_name}.")

if __name__ == "__main__":
    main()
    
    
    
# print('Querying MongoDB')

# query_circle = gpd.GeoSeries([point], crs=4326).to_crs(epsg=utm_epsg).buffer(radius_meters).to_crs(epsg=4326).iloc[0].__geo_interface__
# with open('temp.json', 'w') as f:
#     json.dump(query_circle, f)
# db_results = util.find_intersecting_features('census-dashboard', 'state-geojson', query_circle)
# # print the ObjectIds
# print([str(result['NAME']) for result in db_results])