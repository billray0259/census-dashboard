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

app = Flask(__name__)

# Initialize the Dash app with Bootstrap stylesheet
dash_app = dash.Dash(__name__, server=app, url_base_pathname='/', external_stylesheets=[dbc.themes.BOOTSTRAP])

# Load the shapefile
shapefile_path = 'data/shape-files/state/2023/tl_2023_us_state.shp'
states_gdf = gpd.read_file(shapefile_path)

# Convert GeoDataFrame to GeoJSON format
states_geojson = states_gdf.to_json()

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
            dbc.Col(
                html.P("Welcome to the Census Dashboard!", className="text-center"),
                width=12
            )
        ),
        dbc.Row(
            [
                dbc.Col(
                    dcc.Input(
                        id='table-input',
                        type='text',
                        value='B01001',
                        placeholder='Enter table code',
                        className='text-center'
                    ),
                    width=6,
                    className="mt-3"
                ),
                dbc.Col(
                    dcc.Slider(
                        id='radius-slider',
                        min=1,
                        max=20,
                        step=0.5,
                        value=5,
                        marks={i: f'{i} mi' for i in range(1, 21)},
                        tooltip={"placement": "bottom", "always_visible": True}
                    ),
                    width=6,
                    className="mt-3"
                )
            ]
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
                dcc.Loading(html.Div(id="click-output", className="text-center")),
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
                html.Div(id="data-table", className="text-center"),  # New Div for data table
                width=12,
                className="mt-3"
            )
        ),
        dcc.Store(id="state-storage")  # Store object to store state
    ],
    fluid=True,
)

@dash_app.callback(
    [Output("click-output", "children"),
     Output("circle-layer", "children"),
     Output("highlight-layer", "children"),
     Output("state-storage", "data"),
     Output("data-table", "children")],  # New Output for data table
    [Input("map", "clickData"),
     Input("radius-slider", "value"),
     Input("table-input", "value")],  # New Input for table code
    [State("map", "center"),
     State("map", "zoom"),
     State("state-storage", "data")]
)
def display_coordinates_and_state(clickData, radius, table_code, center, zoom, stored_state):
    click_output = "Click on the map to get coordinates."
    circle_layer = []
    highlight_layer = dash.no_update
    state_storage = stored_state
    data_table = dash.no_update  # Initialize data_table

    if clickData is not None:
        lat, lng = float(clickData['latlng']['lat']), float(clickData['latlng']['lng'])
        utm_epsg = util.get_utm_epsg(lat, lng)
        
        # Create a point from the click coordinates
        point = Point(lng, lat)
        
        # Filter block groups within the selected radius
        radius_meters = radius * 1609.34  # Convert miles to meters
        
        projected_states_gdf = states_gdf.to_crs(epsg=utm_epsg)
        
        projected_point = gpd.GeoSeries([point], crs=4326).to_crs(epsg=utm_epsg).iloc[0]
        
        # Create a circle around the click point with the selected radius
        circle = projected_point.buffer(radius_meters)  # Radius in meters
        
        intersecting_states = projected_states_gdf[projected_states_gdf.intersects(circle)]
        block_group_shapefile_paths = [
            f'data/shape-files/block-group/2023/tl_2023_{state_fp}_bg.shp'
            for state_fp in intersecting_states['STATEFP']
        ]
        
        if not block_group_shapefile_paths:
            click_output = f"Latitude: {lat:.6f}, Longitude: {lng:.6f}, State: Not Found"
            circle = dl.Circle(center=(lat, lng), radius=radius_meters,  # Radius in meters
                               color='red', fill=True, fillOpacity=0)
            circle_layer = [circle]
            return click_output, circle_layer, highlight_layer, state_storage, data_table
        
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
        
        print(block_group_gdf.head())
        data_df = cl.aggregate_blockgroups(table_code, block_group_gdf)  # Use table_code from input
        
        # format data_df['Value'] as comma-separated integers
        data_df['Value'] = data_df['Value'].apply(lambda x: f'{round(x):,}' if pd.notna(x) else '')
        
        # Create a DataTable from the dataframe
        data_table = dash_table.DataTable(
            columns=[{"name": i, "id": i} for i in data_df.columns],
            data=data_df.to_dict('records'),
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left'},
            style_header={
            'backgroundColor': 'rgb(30, 30, 30)',
            'color': 'white'
            },
            style_data={
            'backgroundColor': 'rgb(50, 50, 50)',
            'color': 'white'
            },
            style_data_conditional=[
            {
                'if': {'column_id': 'Value'},
                'textAlign': 'center',
                'format': {'specifier': ',d'}
            }
            ]
        )
        
        geojson_data = block_group_gdf.__geo_interface__
        
        highlight_layer = [
            dl.GeoJSON(
                data=d,
                options=dict(style=dict(color="blue", weight=1, fillOpacity=overlap)),
            )
            for d, overlap in zip(geojson_data['features'], block_group_gdf['percent_overlap']*0.5)
        ]
        
        circle = dl.Circle(center=(lat, lng), radius=radius_meters,  # Radius in meters
                           color='red', fill=True, fillOpacity=0)
        circle_layer = [circle]
    
        click_output = f"Latitude: {lat:.6f}, Longitude: {lng:.6f}, State: {intersecting_states['STUSPS'].values}"
        
    return click_output, circle_layer, highlight_layer, state_storage, data_table  # Return data_table

if __name__ == "__main__":
    app.run(debug=True)
