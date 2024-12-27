import dotenv
dotenv.load_dotenv('.env')
import os
from census import Census
import numpy as np

from openai import OpenAI

import requests
import pandas as pd

ai = OpenAI()
census = Census(os.getenv('CENSUS_API_KEY'))
acs5 = census.acs5



def aggregate_blockgroups(table, block_group_gdf):
    percent_overlap = block_group_gdf['percent_overlap'] if 'percent_overlap' in block_group_gdf.columns else np.ones(len(block_group_gdf))
    ucgids = block_group_gdf['GEOIDFQ']
    bg_data = fetch_census_data(table, ucgids)
    
    # parse numbers
    for col in bg_data.columns:
        try:
            bg_data[col] = pd.to_numeric(bg_data[col])
        except ValueError:
            pass
    
    # dot product every numeric column with percent_overlap
    data = {}
    for col in bg_data.columns:
        col_type = bg_data[col].dtype
        if col_type == np.float64 or col_type == np.int64:
            bg_data[col] = bg_data[col].astype(np.float64)
            data[col] = np.dot(bg_data[col], percent_overlap)
    
    vars = variables(table)
    rows = [
        {'VarID': key, 'Variable': vars[key]['label'].replace('!!', ' '), 'Value': value}
        for key, value in data.items()
    ]
    
    df = pd.DataFrame(rows).dropna(how='all')
    return df



    




def fetch_census_data(group_name, ucgid_list):
    """
    Fetches data from the U.S. Census Bureau API for a specified group and list of ucgids.

    Parameters:
    - group_name (str): The name of the data group to retrieve.
    - ucgid_list (list): A list of ucgids (Uniform Census Geography Identifiers).

    Returns:
    - pd.DataFrame: A DataFrame containing the retrieved data.
    """
    if len(ucgid_list) > 100:
        chunks = [ucgid_list[i:i + 100] for i in range(0, len(ucgid_list), 100)]
        return pd.concat([fetch_census_data(group_name, chunk) for chunk in chunks])
    
    # Base URL for the Census API
    base_url = "https://api.census.gov/data/2022/acs/acs5"

    # Convert the list of ucgids into a comma-separated string
    ucgid_str = ",".join(ucgid_list)

    # Construct the API request parameters
    params = {
        "get": f"group({group_name})",
        "ucgid": ucgid_str,
        "key": os.getenv("CENSUS_API_KEY"),
    }

    # Make the API request
    response = requests.get(base_url, params=params)

    # Check for a successful response
    if response.status_code == 200:
        # Parse the JSON response
        data = response.json()

        # The first row contains the column headers
        headers = data[0]

        # The subsequent rows contain the data
        rows = data[1:]

        # Create a DataFrame
        df = pd.DataFrame(rows, columns=headers)

        return df
    else:
        # Handle errors
        raise Exception(f"API request failed with status code {response.status_code}: {response.text}")


def variables(table, year=2023):
    """
    Returns a list of the variables available from this source.
    """
    
    variables_url = 'https://api.census.gov/data/%s/acs/acs5/groups/%s.json'

    # Query the table metadata as raw JSON
    tables_url = variables_url % (str(year), table)
    params = {
        "key": os.getenv("CENSUS_API_KEY"),
    }
    resp = requests.get(tables_url, params=params)

    # Pass it out
    return resp.json()['variables']