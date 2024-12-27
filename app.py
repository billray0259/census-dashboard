from flask import Flask
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table
from dash.dependencies import Input, Output, State
import dash_leaflet as dl
import geopandas as gpd
from shapely.geometry import Point, shape
import util
import base64
import pandas as pd
import census_lib as cl
import json
import numpy as np
from dash import callback_context
from dash.exceptions import PreventUpdate

app = Flask(__name__)

# Initialize the Dash app with Bootstrap stylesheet
dash_app = dash.Dash(__name__, server=app, url_base_pathname='/', external_stylesheets=[dbc.themes.SPACELAB])

# 5 miles
DEFAULT_RADIUS = 5 * 1609.34

BLANK_GEOJSON = {
    "type": "FeatureCollection",
    "features": []
}

# Define the layout of the Dash app
dash_app.layout = dbc.Container(
    [
        dbc.Row(
            dbc.Col(
                html.H1(
                    [
                        "Census Dashboard",
                        
                    ],
                    className="text-center"
                ),
                width=12
            )
        ),
        dbc.Row(
            dbc.Col([
                dbc.Button(
                    'Help',
                    id="open-help-button",
                    color="link",
                    className="ml-2",
                    style={"fontSize": "1.5rem"}
                ),
                dbc.Collapse(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H4("How to Use the App", className="card-title"),
                                html.Ol(
                                    [
                                        html.Li("Search or enter table codes."),
                                        html.Li("Click on the map to select an area of interest."),
                                        html.Li("Adjust the radius as needed."),
                                        html.Li("Give your area a name."),
                                        html.Li("Click 'Add Point' to add the area to your query."),
                                        html.Li("Click 'Get Data'."),
                                        html.Li("Click 'Download Data' to export the results table as a csv file.")
                                    ]
                                ),
                                dbc.Button("Close", id="close-help-button", color="secondary", className="mt-3")
                            ]
                        ),
                        className="mb-3"
                    ),
                    id="help-panel",
                    is_open=True
                ),
                ],
                width=12
            )
        ),
        dbc.Row([
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.H4("Table Codes", className="card-title"),
                            html.P("Enter table codes (comma-separated):"),
                            dbc.Input(
                                id='table-input',
                                type='text',
                                placeholder='e.g. B01001,B01002',
                                className='mb-3'
                            ),
                            dbc.InputGroup(
                                [
                                    dbc.Input(id="table-search-input", placeholder="Search for a table..."),
                                    dbc.Button("Search", id="table-search-button", n_clicks=0)
                                ],
                                className="mb-3"
                            ),
                            html.H4("Points of Interest", className="card-title"),
                            html.P("Point of Interest Name:"),
                            dbc.InputGroup(
                                [
                                    dbc.Input(
                                        id='poi-name-input',
                                        type='text',
                                        placeholder='Enter a name for your point',
                                    ),
                                    dbc.Button("Add Point", id="add-point-button", color="primary")
                                ],
                                className="mb-3"
                            ),
                            html.H4("Points of Interest List", className="card-title"),
                            html.Ul(id='points-list', className='list-group'),
                            html.H4("Radius", className="card-title mt-3"),
                            dbc.InputGroup(
                                [
                                    html.Div(
                                        dcc.Slider(
                                            id='radius-slider',
                                            min=1,
                                            max=15,
                                            value=5,
                                            step=1,
                                            marks={i: f'{i}' for i in range(1, 16, 2)},
                                            tooltip={"placement": "bottom"},
                                            className="ml-3",
                                        ),
                                        style={'width': '70%'}  # Allocate 70% width to the slider
                                    ),
                                    dbc.Input(
                                        id='radius-input',
                                        type='number',
                                        min=0.1,
                                        value=5,
                                        style={'width': '10%'}  # Allocate 20% width to the input
                                    ),
                                    dbc.Select(
                                        id='unit-toggle',
                                        options=[
                                            {'label': 'Miles', 'value': 'miles'},
                                            {'label': 'Kilometers', 'value': 'km'}
                                        ],
                                        value='miles',
                                        style={'width': '20%'}  # Allocate 10% width to the select
                                    )
                                ],
                                className="d-flex align-items-center mt-3"  # Use flexbox for layout
                            ),
                            dcc.Upload(
                                id='geojson-upload',
                                children=html.Div([
                                    'Upload GeoJSON: Drag and Drop or ',
                                    html.A('Select Files')
                                ]),
                                style={
                                    'width': '100%',
                                    'height': '60px',
                                    'lineHeight': '60px',
                                    'borderWidth': '1px',
                                    'borderStyle': 'dashed',
                                    'borderRadius': '5px',
                                    'textAlign': 'center',
                                    'margin': '10px'
                                },
                                # Allow multiple files to be uploaded
                                multiple=False
                            ),
                            dbc.Button("Get Data", id="get-data-button", color="primary", className="mt-3"),
                        ]
                    ),
                    className="mb-3"
                ),
                width=4
            ),
            dbc.Col(
                dl.Map(
                    center={'lat': 40, 'lng': -100},  # Initial center of the map
                    zoom=4,             # Initial zoom level
                    children=[
                        dl.TileLayer(),  # Base layer
                        dl.LayerGroup(id="circle-layer"),  # Layer group for the circle
                        dl.LayerGroup(id="prev-circle-layer"),  # Layer group for the circle
                        dl.LayerGroup(id="highlight-layer")  # Layer group for the highlighted state
                    ],
                    id="map",            # ID to reference in callbacks
                    style={'width': '100%', 'height': '50vh'}
                ),
                width=8,
                className="mt-3 mb-3"
            )
        ]),
        dbc.Row(
            dbc.Col(
                dcc.Loading(dash_table.DataTable(
                    id="search-output-table",
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
                    row_selectable='multi',  # Allow multiple rows to be selected
                    selected_rows=[]
                )),  # Change Div to DataTable
                width=12
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
        dcc.Store(id="geo-json-store", data=BLANK_GEOJSON),  # Store for GeoJSON data
        dcc.Store(id="search-output"),  # Store for search results
    ],
    fluid=True,
)

@dash_app.callback(
    [Output("help-panel", "is_open"), Output("open-help-button", "style")],
    [Input("open-help-button", "n_clicks"), Input("close-help-button", "n_clicks")],
    [State("help-panel", "is_open")]
)
def toggle_help_panel(open_clicks, close_clicks, is_open):
    if open_clicks or close_clicks:
        is_open = not is_open
    button_style = {"display": "none"} if is_open else {"fontSize": "1.5rem"}
    return is_open, button_style

@dash_app.callback(
    Output("search-output", "data"),
    Output("search-output-table", "selected_rows"),
    Input("table-search-button", "n_clicks"),
    State("table-search-input", "value")
)
def search_table(n_clicks, query):
    if n_clicks > 0 and query:
        results = util.semantic_search_2023_tables(query)
        results = pd.DataFrame(results)
        results.drop(columns=['_id'], inplace=True)
        return results.to_dict('records'), []
    return [], []

@dash_app.callback(
    Output("search-output-table", "data"),
    Output("search-output-table", "columns"),
    Input("search-output", "data")
)
def update_search_output_table(data):
    if data:
        columns = [{"name": i, "id": i} for i in data[0].keys()]
        return data, columns
    return [], []

@dash_app.callback(
    Output("table-input", "value"),
    Input("search-output-table", "derived_virtual_selected_rows"),
    State("search-output-table", "data"),
    State("table-input", "value")
)
def update_table_input(selected_rows, table_data, current_value):
    print('selected_rows:', selected_rows)
    if selected_rows is None or table_data is None:
        return current_value

    if current_value is None:
        current_value = ''

    selected_table_codes = [table_data[i]['name'] for i in selected_rows]
    current_table_codes = [code.strip() for code in current_value.split(',') if code.strip()]
    updated_table_codes = list(set(current_table_codes + selected_table_codes))

    return ','.join(updated_table_codes)

@dash_app.callback(
    [Output("click-output", "children"),
     Output("circle-layer", "children")],  # New Output for data table
    [Input("map", "clickData"),
     Input("radius-input", "value"),
     Input("unit-toggle", "value")],
)
def display_coordinates_and_state(clickData, radius, unit):
    click_output = "Click on the map to get coordinates."
    circle_layer = []

    if clickData is not None and radius is not None:
        lat, lng = float(clickData['latlng']['lat']), float(clickData['latlng']['lng'])
        radius_meters = radius * 1609.34 if unit == 'miles' else radius * 1000  # Convert to meters
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

def make_geojson_circle(lat, lng, radius_meters):
    geo_json = {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [lng, lat]
        },
        "properties": {
            "radius": radius_meters
        }
    }
    return geo_json
# Add a new combined callback to handle adding, saving, and removing points
@dash_app.callback(
    Output("geo-json-store", "data"),
    [
        Input('add-point-button', 'n_clicks'),
        Input('geojson-upload', 'contents'),
        Input({'type': 'save-point-button', 'index': dash.dependencies.ALL}, 'n_clicks'),
        Input({'type': 'remove-point-button', 'index': dash.dependencies.ALL}, 'n_clicks')
    ],
    [
        State('geo-json-store', 'data'),
        State('poi-name-input', 'value'),
        State('map', 'clickData'),
        State('radius-slider', 'value'),  # Add radius state
        State('unit-toggle', 'value'),  # Add unit state
        State({'type': 'point-name-input', 'index': dash.dependencies.ALL}, 'value'),
        State({'type': 'remove-point-button', 'index': dash.dependencies.ALL}, 'id')
    ],
    prevent_initial_call=True
)
def handle_points(add_clicks, contents, save_clicks, remove_point_clicks, geo_json, point_name, clickData, radius, unit, names, remove_ids):
    ctx = callback_context
    if not ctx.triggered:
        return geo_json

    triggered = ctx.triggered[0]
    triggered_id = triggered['prop_id'].split('.')[0]

    if triggered_id == 'add-point-button':
        if clickData:
            lat = float(clickData['latlng']['lat'])
            lng = float(clickData['latlng']['lng'])
            radius_meters = radius * 1609.34 if unit == 'miles' else radius * 1000  # Convert to meters
            new_feature = make_geojson_circle(lat, lng, radius_meters)
            new_feature["properties"]["name"] = point_name.strip() if point_name else f"Point {len(geo_json['features']) + 1}"
            geo_json['features'].append(new_feature)

    elif triggered_id == 'geojson-upload':
        if contents is None:
            raise PreventUpdate

        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        new_geo_json = json.loads(decoded)
        if 'features' not in new_geo_json or not new_geo_json['features']:
            raise PreventUpdate
        for i, feature in enumerate(new_geo_json['features']):
            if feature["geometry"]["type"] == "Point":
                if 'properties' not in feature:
                    feature['properties'] = {
                        "name": f"Uploaded Point {i + 1}",
                        "radius": DEFAULT_RADIUS
                    }
                if 'radius' not in feature['properties']:
                    feature['properties']['radius'] = DEFAULT_RADIUS
                if 'name' not in feature['properties']:
                    feature['properties']['name'] = f"Uploaded Point {i + 1}"
            else:
                # just insert feature as is
                if "properties" not in feature:
                    feature["properties"] = {}
                if "name" not in feature["properties"]:
                    feature["properties"]["name"] = f"Uploaded Feature {i + 1}"
                geo_json['features'].append(feature)
        geo_json['features'] += new_geo_json['features']
        return geo_json

    else:
        button_id = json.loads(triggered_id)
        if button_id['type'] == 'save-point-button':
            index = button_id['index']
            if names[index]:
                radius_meters = radius * 1609.34 if unit == 'miles' else radius * 1000  # Convert to meters
                lat = geo_json["features"][index]["geometry"]["coordinates"][1]
                lng = geo_json["features"][index]["geometry"]["coordinates"][0]
                updated_feature = make_geojson_circle(lat, lng, radius_meters)
                updated_feature["properties"]["name"] = names[index].strip()
                updated_feature["properties"]["radius"] = radius_meters
                print(names[index].strip())
                geo_json['features'][index] = updated_feature
        
        elif button_id['type'] == 'remove-point-button':
            index = button_id['index']
            if 0 <= index < len(geo_json['features']):
                geo_json['features'].pop(index)
    return geo_json

@dash_app.callback(
    Output("prev-circle-layer", "children"),
    [  
        Input("geo-json-store", "data")
    ],
)
def update_circles_layer(geo_json):
    circle_layer = []
    for feature in geo_json['features']:
        if feature['geometry']['type'] == 'Point':
            lng, lat = feature['geometry']['coordinates']
            radius = feature['properties']['radius']
            name = feature['properties']['name']
            circle_layer.append(
                dl.Circle(
                    center=(lat, lng),
                    radius=radius,  # Radius is already in meters
                    color='green', 
                    fill=True, 
                    fillOpacity=0.1
                )
            )
            print(name)
            circle_layer.append(
                dl.Marker(
                    position=[lat, lng],
                    children=[dl.Tooltip(content=name)]
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
        State("geo-json-store", "data"),
        State("table-input", "value")
    ],
    prevent_initial_call=True
)
def search_census(_, geo_json_data, table_codes_input):
    if len(geo_json_data['features']) == 0:
        return html.Div("No Features defined."), []

    table_codes = [tc.strip() for tc in table_codes_input.split(',') if tc.strip()]

    if not table_codes:
        return html.Div("No valid table codes provided."), []

    final_list = []
    final_block_groups = []

    for feature in geo_json_data['features']:
        if feature['geometry']['type'] != 'Point':
            return html.Div("Invalid GeoJSON data."), []
        # lng, lat = float(feature['lat']), float(p['lng'])
        lng, lat = feature['geometry']['coordinates']
        radius_meters = feature["properties"]['radius']  # Radius is already in meters
        utm_epsg = util.get_utm_epsg(lat, lng)
    
        point = Point(lng, lat)
        projected_point = gpd.GeoSeries([point], crs=4326).to_crs(epsg=utm_epsg).iloc[0]
        
        # Create a circle around the click point with the selected radius
        circle = projected_point.buffer(radius_meters)  # Radius in meters
        
        print('Querying MongoDB')

        query_circle = gpd.GeoSeries([point], crs=4326).to_crs(epsg=utm_epsg).buffer(radius_meters).to_crs(epsg=4326).iloc[0].__geo_interface__
        db_results = util.find_intersecting_features('census-dashboard', 'block-group-geojson', query_circle)
        print(db_results[0].keys())
        db_results = [{'geometry': doc['geometry'], **doc['properties']} for doc in db_results]
        print(f'Number of block groups: {len(db_results)}')
        print(db_results[0].keys())
        db_results = pd.DataFrame(db_results)
        db_results['geometry'] = db_results['geometry'].apply(shape)
        block_group_gdf = gpd.GeoDataFrame(db_results)
        block_group_gdf.set_geometry('geometry')
        block_group_gdf = block_group_gdf.set_crs("EPSG:4326")  # Adjust if your CRS is different
        
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
            print(block_group_gdf)
            data_df = cl.aggregate_blockgroups(table_code, block_group_gdf)  # Use table_code from input
            data_df["Value"] = data_df["Value"].apply(lambda x: f"{round(x):,}" if pd.notna(x) else "")
            data_df = data_df[data_df["VarID"].str.endswith("E")]
            print(feature['properties']['name'])
            data_df['point_name'] = feature['properties']['name']
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

# Callback to display the list of points with edit and remove buttons
@dash_app.callback(
    Output('points-list', 'children'),
    [
        Input('geo-json-store', 'data')
    ]
)
def display_points(geo_json):
    return [
        dbc.InputGroup(
            [
                dbc.Input(
                    id={'type': 'point-name-input', 'index': i},
                    type='text',
                    value=feature['properties']['name'],
                ),
                dbc.Button(
                    "Save",
                    id={'type': 'save-point-button', 'index': i},
                    color="primary",
                    size="sm",
                ),
                dbc.Button(
                    "Remove",
                    id={'type': 'remove-point-button', 'index': i},
                    color="danger",
                    size="sm"
                )
            ],
            className='list-group-item d-flex align-items-center'
        )
        for i, feature in enumerate(geo_json['features'])
    ]

@dash_app.callback(
    Output('radius-slider', 'value'),
    Output('radius-input', 'value'),
    Output('radius-slider', 'max'),
    Output('radius-slider', 'marks'),
    Input('radius-slider', 'value'),
    Input('radius-input', 'value'),
    Input('unit-toggle', 'value')
)
def sync_radius_inputs(slider_value, input_value, unit):
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate

    max_value = 15 if unit == 'miles' else 25
    marks = {i: f'{i}' for i in range(1, max_value + 1, 2)}

    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if triggered_id == 'radius-slider':
        return slider_value, slider_value, max_value, marks
    elif triggered_id == 'radius-input':
        return input_value, input_value, max_value, marks
    elif triggered_id == 'unit-toggle':
        return slider_value, slider_value, max_value, marks
    raise PreventUpdate


if __name__ == "__main__":
    app.run(debug=True)
