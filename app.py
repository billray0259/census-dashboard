from flask import Flask
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table
from dash.dependencies import Input, Output, State
import dash_leaflet as dl
import geopandas as gpd
from shapely.geometry import Point
import util
import pandas as pd
import census_lib as cl
import json
import numpy as np

app = Flask(__name__)

# Initialize the Dash app with Bootstrap stylesheet
dash_app = dash.Dash(__name__, server=app, url_base_pathname='/', external_stylesheets=[dbc.themes.BOOTSTRAP])

# Load the shapefile
shapefile_path = 'data/shape-files/state/2023/tl_2023_us_state.shp'
states_gdf = gpd.read_file(shapefile_path)

# Convert GeoDataFrame to GeoJSON format
states_geojson = states_gdf.to_json()

with open('data/2023_tables.json', 'r') as f:
    tables_2023 = json.load(f)

tables_2023_df = pd.DataFrame(tables_2023)
tables_2023_embeddings = np.load('data/2023_table_embeddings.npy')

# Define the layout of the Dash app
dash_app.layout = dbc.Container(
    [
        dbc.Row(
            dbc.Col(
                html.H1("Census Dashboard", className="text-center"),
                width=12
            )
        ),
        dbc.Row(
            [
                dbc.Col(
                    html.Div(
                        [
                            html.P("Enter table codes (comma-separated):"),
                            dbc.Input(
                                id='table-input',
                                type='text',
                                value='B01001,B01002',
                                placeholder='e.g. B01001,B01002',
                                className='mb-3'
                            ),
                            html.P("Point of Interest Name:"),
                            dbc.Input(
                                id='poi-name-input',
                                type='text',
                                value='My Point',
                                placeholder='Enter a name for your point',
                                className='mb-3'
                            ),
                            dbc.Button("Add Point", id="add-point-button", color="primary", className="mr-2"),
                            dbc.Button("Remove Last Point", id="remove-point-button", color="danger", className="ml-2"),
                        ]
                    ),
                    width=4
                ),
                dbc.Col(
                    dcc.Slider(
                        id='radius-slider',
                        min=1,
                        max=20,
                        step=0.5,
                        value=5,
                        marks={i: f'{i} mi' for i in range(1, 21)},
                        tooltip={"placement": "bottom", "always_visible": True},
                        className="mt-4"
                    ),
                    width=8
                ),
            ]
        ),
        dbc.Row(
            dbc.Col(
                dbc.InputGroup(
                    [
                        dbc.Input(id="table-search-input", placeholder="Search for a table..."),
                        dbc.Button("Search", id="table-search-button", n_clicks=0)
                    ],
                    className="mt-3"
                ),
                width=12
            )
        ),
        dbc.Row(
            dbc.Col(
                dcc.Loading(html.Div(id="search-output", className="text-center mt-3")),  # Change Div to DataTable
                width=12
            )
        ),
        dbc.Row(
            dbc.Col(
                dl.Map(
                    center={'lat': 40, 'lng': -100},  # Initial center of the map
                    zoom=4,             # Initial zoom level
                    children=[
                        dl.TileLayer(),  # Base layer
                        dl.GeoJSON(data=states_geojson, id="state-polygons"),  # State polygons
                        dl.LayerGroup(id="circle-layer"),  # Layer group for the circle
                        dl.LayerGroup(id="prev-circle-layer"),  # Layer group for the circle
                        dl.LayerGroup(id="highlight-layer")  # Layer group for the highlighted state
                    ],
                    id="map",            # ID to reference in callbacks
                    style={'width': '100%', 'height': '50vh'}
                ),
                width=12,
                className="mt-3 mb-3"
            )
        ),
        dbc.Row(
            dbc.Col(
                dbc.Button("Get Data", id="get-data-button", color="primary", className="mt-3"),  # New Button
                width=12,
                className="text-center"
            )
        ),
        dbc.Row(
            dbc.Col(
                html.Div(id="click-output", className="text-center"),
                width=12,
                className="mt-3"
            )
        ),
        dbc.Row(
            dbc.Col(
                html.Div(id="camera-output", className="text-center"),
                width=12
            )
        ),
        dbc.Row(
            dbc.Col(
                dcc.Loading(html.Div(id="data-table", className="text-center")),  # New Div for data table
                width=12,
                className="mt-3"
            )
        ),
        dbc.Row(
            dbc.Col(
                dbc.Button("Download Data", id="download-button", color="secondary", className="mt-3"),
                width=12,
                className="text-center"
            )
        ),
        dcc.Download(id="download-dataframe-csv"),
        dcc.Store(id="state-storage"),  # Store object to store state
        dcc.Store(id="table-data-storage"),
        dcc.Store(id="points-store", data=[]),   # List of points of interest
    ],
    fluid=True,
)

@dash_app.callback(
    Output("search-output", "children"),
    Input("table-search-button", "n_clicks"),
    State("table-search-input", "value")
)
def search_table(n_clicks, query):
    if n_clicks > 0 and query:
        query_embedding = util.embed([query])[0]
        scores = np.dot(tables_2023_embeddings, query_embedding)
        arg_sort = np.argsort(scores)[::-1][:8]
        filtered_df = tables_2023_df.iloc[arg_sort]
        return dash_table.DataTable(
            columns=[{"name": i, "id": i} for i in filtered_df.columns],
            data=filtered_df.to_dict('records'),
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left'},
            style_header={
                'backgroundColor': 'rgb(30, 30, 30)',
                'color': 'white'
            },
            style_data={
                'backgroundColor': 'rgb(50, 50, 50)',
                'color': 'white'
            }
        )
    return dash.no_update

@dash_app.callback(
    [Output("click-output", "children"),
     Output("circle-layer", "children")],  # New Output for data table
    [Input("map", "clickData"),
     Input("radius-slider", "value")],
)
def display_coordinates_and_state(clickData, radius):
    click_output = "Click on the map to get coordinates."
    circle_layer = []

    if clickData is not None:
        lat, lng = float(clickData['latlng']['lat']), float(clickData['latlng']['lng'])
        radius_meters = radius * 1609.34  # Convert miles to meters
        dl_circle = dl.Circle(center=(lat, lng), radius=radius_meters,  # Radius in meters
                           color='red', fill=True, fillOpacity=0)
        circle_layer = [dl_circle]
        click_output = f"Latitude: {lat:.6f}, Longitude: {lng:.6f}"
        
    return click_output, circle_layer


def make_geo_circle(lat, lng, radius_meters):
    utm_epsg = util.get_utm_epsg(lat, lng)
    
    point = Point(lng, lat)
    projected_point = gpd.GeoSeries([point], crs=4326).to_crs(epsg=utm_epsg).iloc[0]
    
    # Create a circle around the click point with the selected radius
    circle = projected_point.buffer(radius_meters)  # Radius in meters
    
    return circle


@dash_app.callback(
    Output("points-store", "data"),
    [Input("add-point-button", "n_clicks"),
     Input("remove-point-button", "n_clicks")],
    [
        State("points-store", "data"),
        State("poi-name-input", "value"),
        State("map", "clickData")
    ],
    prevent_initial_call=True
)
def update_points(add_clicks, remove_clicks, points, point_name, clickData):
    """
    - Add a new point with the name from poi-name-input if Add is clicked
      and if there's a recent map click.
    - Remove the last point if Remove is clicked.
    - 'points' is a list of dicts: [{'name':..., 'lat':..., 'lng':...}, ...].
    """
    ctx = dash.callback_context
    if not ctx.triggered:
        return points  # No change
    
    # Check which button was triggered
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if triggered_id == 'add-point-button':
        # Add a new point if we have valid click data
        if clickData:
            lat = float(clickData['latlng']['lat'])
            lng = float(clickData['latlng']['lng'])
            new_point = {
                'name': point_name.strip() if point_name else f"Point {len(points)+1}",
                'lat': lat,
                'lng': lng
            }
            points.append(new_point)
        return points

    elif triggered_id == 'remove-point-button':
        # Remove the last point
        if len(points) > 0:
            points.pop()
        return points

    return points

@dash_app.callback(
    Output("prev-circle-layer", "children"),
    [Input("points-store", "data"),
     Input("radius-slider", "value")],
)
def update_circles_layer(points, radius):
    """
    Draw a circle for each point in 'points-store'.
    """
    circle_layer = []
    radius_meters = radius * 1609.34
    
    for p in points:
        circle_layer.append(
            dl.Circle(
                center=(p['lat'], p['lng']),
                radius=radius_meters,
                color='green', 
                fill=True, 
                fillOpacity=0.1
            )
        )
    return circle_layer

@dash_app.callback(
    [
        Output("data-table", "children"),
        Output("highlight-layer", "children"),
        Output("table-data-storage", "data"), 
    ],
    [Input("get-data-button", "n_clicks")],
    [
        State("points-store", "data"),
        State("radius-slider", "value"),
        State("table-input", "value")
    ],
    prevent_initial_call=True
)
def search_census(_, points, radius, table_codes_input):
    if not points:
        return html.Div("No points defined."), []

    table_codes = [tc.strip() for tc in table_codes_input.split(',') if tc.strip()]

    if not table_codes:
        return html.Div("No valid table codes provided."), []

    final_list = []
    final_block_groups = []

    for p in points:
        lat, lng = float(p['lat']), float(p['lng'])
        radius_meters = radius * 1609.34  # Convert miles to meters
        utm_epsg = util.get_utm_epsg(lat, lng)
    
        point = Point(lng, lat)
        projected_point = gpd.GeoSeries([point], crs=4326).to_crs(epsg=utm_epsg).iloc[0]
        
        # Create a circle around the click point with the selected radius
        circle = projected_point.buffer(radius_meters)  # Radius in meters
        
        projected_states_gdf = states_gdf.to_crs(epsg=utm_epsg)
        intersecting_states = projected_states_gdf[projected_states_gdf.intersects(circle)]
        
        block_group_shapefile_paths = [
            f'data/shape-files/block-group/2023/tl_2023_{state_fp}_bg.shp'
            for state_fp in intersecting_states['STATEFP']
        ]
        
        if not block_group_shapefile_paths:
            return data_table, highlight_layer
        
        # read all and concatenate
        block_group_gdf = gpd.GeoDataFrame()
        for path in block_group_shapefile_paths:
            block_group_gdf = pd.concat([block_group_gdf, gpd.read_file(path)])
        
        projected_gdf = block_group_gdf.to_crs(epsg=utm_epsg)
        projected_gdf['distance'] = projected_gdf.centroid.distance(projected_point)
            
        # Convert to appropriate CRS before converting to GeoJSON
        block_group_gdf = block_group_gdf.to_crs(epsg=4326)
        
        # Project the circle to the same CRS as block_group_gdf
        projected_circle = gpd.GeoSeries([circle], crs=utm_epsg).to_crs(epsg=4326).iloc[0]
        
        block_group_gdf['percent_overlap'] = block_group_gdf.geometry.apply(
            lambda geom: geom.intersection(projected_circle).area / geom.area if not geom.is_empty else 0
        )
        
        block_group_gdf = block_group_gdf[block_group_gdf['percent_overlap'] > 0]
        
        print(f'Number of block groups: {len(block_group_gdf)}')
        for table_code in table_codes:
            data_df = cl.aggregate_blockgroups(table_code, block_group_gdf)  # Use table_code from input
            data_df["Value"] = data_df["Value"].apply(lambda x: f"{round(x):,}" if pd.notna(x) else "")
            data_df = data_df[data_df["VarID"].str.endswith("E")]
            data_df['point_name'] = p['name']
            final_list.append(data_df)

        # geojson_data = block_group_gdf.__geo_interface__
        final_block_groups.append(block_group_gdf)
    
    if not final_list:
        return html.Div("No data found for these points/tables."), []

    big_df = pd.concat(final_list, ignore_index=True)

    # Pivot so that VarID values become columns
    # We'll make each row: (point_name)
    # The columns: each VarID
    pivot_df = big_df.pivot_table(
        index='point_name',
        columns='Variable',
        values='Value',
        aggfunc='first'  
    ).reset_index()

    # Build DataTable
    columns = [{"name": str(col), "id": str(col)} for col in pivot_df.columns]
    data_table = dash_table.DataTable(
        columns=columns,
        data=pivot_df.to_dict('records'),
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'left'},
        style_header={'backgroundColor': 'rgb(30, 30, 30)', 'color': 'white'},
        style_data={'backgroundColor': 'rgb(50, 50, 50)', 'color': 'white'},
    )
    final_block_group_gdf = pd.concat(final_block_groups, ignore_index=True)
    print(min(final_block_group_gdf['percent_overlap']), max(final_block_group_gdf['percent_overlap']))

    final_geo_json = final_block_group_gdf.__geo_interface__

    highlight_layer = [
        dl.GeoJSON(
            data=d,
            options=dict(style=dict(color="blue", weight=1, fillOpacity=overlap)),
        )
        for d, overlap in zip(final_geo_json["features"], final_block_group_gdf['percent_overlap']*0.5)
    ]

    return data_table, highlight_layer, pivot_df.to_dict("records"),

@dash_app.callback(
    Output("download-dataframe-csv", "data"),
    Input("download-button", "n_clicks"),
    State("table-data-storage", "data"),
    prevent_initial_call=True
)
def download_data(n_clicks, table_data):
    if not table_data:
        # If there's no table data, do nothing
        return dash.no_update
    
    # Convert stored records back to DataFrame
    df = pd.DataFrame(table_data)
    
    # Use dcc.send_data_frame to send CSV
    return dcc.send_data_frame(df.to_csv, "census_data.csv", index=False)

if __name__ == "__main__":
    app.run(debug=True)
