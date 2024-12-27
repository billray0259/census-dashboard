from dotenv import load_dotenv
load_dotenv()
from pymongo import MongoClient
import os
import numpy as np
import json

with open('data/2023_tables.json', 'r') as f:
    tables = json.load(f)
    
embeddings = np.load('data/2023_table_embeddings.npy')

for table, embedding in zip(tables, embeddings):
    table['embedding'] = embedding.tolist()

client = MongoClient(os.getenv('ATLAS_URI'))
db = client['census-dashboard']
collection = db['2023-tables']

collection.insert_many(tables)