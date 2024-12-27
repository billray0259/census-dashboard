# dash_app/callbacks.py

import json
import base64
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, shape
from dash.dependencies import Input, Output, State, ALL
from dash import dash_table, dcc, html, callback_context
from dash.exceptions import PreventUpdate
import dash
import dash_leaflet as dl
import dash_bootstrap_components as dbc

# Import any custom utilities
import census_dashboard.util as util
import census_dashboard.census_lib as cl

# If you moved these from layout.py constants:
DEFAULT_RADIUS = 5 * 1609.34

def register_callbacks(app):

    @app.callback(
        [Output("help-panel", "is_open"), Output("open-help-button", "style")],
        [Input("open-help-button", "n_clicks"), Input("close-help-button", "n_clicks")],
        [State("help-panel", "is_open")]
    )
    def toggle_help_panel(open_clicks, close_clicks, is_open):
        if open_clicks or close_clicks:
            is_open = not is_open
        button_style = {"display": "none"} if is_open else {"fontSize": "1.5rem"}
        return is_open, button_style

    @app.callback(
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

    @app.callback(
        Output("search-output-table", "data"),
        Output("search-output-table", "columns"),
        Input("search-output", "data")
    )
    def update_search_output_table(data):
        if data:
            columns = [{"name": i, "id": i} for i in data[0].keys()]
            return data, columns
        return [], []

    @app.callback(
        Output("table-input", "value"),
        Input("search-output-table", "derived_virtual_selected_rows"),
        State("search-output-table", "data"),
        State("table-input", "value")
    )
    def update_table_input(selected_rows, table_data, current_value):
        if selected_rows is None or table_data is None:
            return current_value

        if current_value is None:
            current_value = ''

        selected_table_codes = [table_data[i]['name'] for i in selected_rows]
        current_table_codes = [code.strip() for code in current_value.split(',') if code.strip()]
        updated_table_codes = list(set(current_table_codes + selected_table_codes))

        return ','.join(updated_table_codes)

    @app.callback(
        [Output("click-output", "children"),
         Output("circle-layer", "children")],
        [Input("map", "clickData"),
         Input("radius-input", "value"),
         Input("unit-toggle", "value")],
    )
    def display_coordinates_and_state(clickData, radius, unit):
        click_output = "Click on the map to get coordinates."
        circle_layer = []
        if clickData and radius is not None:
            lat, lng = float(clickData['latlng']['lat']), float(clickData['latlng']['lng'])
            radius_meters = radius * 1609.34 if unit == 'miles' else radius * 1000
            dl_circle = dl.Circle(
                center=(lat, lng),
                radius=radius_meters,
                color='red',
                fill=True,
                fillOpacity=0
            )
            circle_layer = [dl_circle]
            click_output = f"Latitude: {lat:.6f}, Longitude: {lng:.6f}"
        return click_output, circle_layer

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

    # Combined callback to handle adding, saving, removing points
    @app.callback(
        Output("geo-json-store", "data"),
        [
            Input('add-point-button', 'n_clicks'),
            Input('geojson-upload', 'contents'),
            Input({'type': 'save-point-button', 'index': ALL}, 'n_clicks'),
            Input({'type': 'remove-point-button', 'index': ALL}, 'n_clicks')
        ],
        [
            State('geo-json-store', 'data'),
            State('poi-name-input', 'value'),
            State('map', 'clickData'),
            State('radius-slider', 'value'),
            State('unit-toggle', 'value'),
            State({'type': 'point-name-input', 'index': ALL}, 'value'),
            State({'type': 'remove-point-button', 'index': ALL}, 'id')
        ],
        prevent_initial_call=True
    )
    def handle_points(add_clicks, contents, save_clicks, remove_point_clicks,
                      geo_json, point_name, clickData, radius, unit, names, remove_ids):
        ctx = callback_context
        if not ctx.triggered:
            return geo_json

        triggered = ctx.triggered[0]
        triggered_id = triggered['prop_id'].split('.')[0]

        if triggered_id == 'add-point-button':
            if clickData:
                lat = float(clickData['latlng']['lat'])
                lng = float(clickData['latlng']['lng'])
                radius_meters = radius * 1609.34 if unit == 'miles' else radius * 1000
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
                    if "properties" not in feature:
                        feature["properties"] = {}
                    if "name" not in feature["properties"]:
                        feature["properties"]["name"] = f"Uploaded Feature {i + 1}"

            geo_json['features'] += new_geo_json['features']
            return geo_json

        else:
            # If a dynamic button was triggered
            button_id_dict = json.loads(triggered_id)
            if button_id_dict['type'] == 'save-point-button':
                index = button_id_dict['index']
                if names[index]:
                    radius_meters = radius * 1609.34 if unit == 'miles' else radius * 1000
                    lat = geo_json["features"][index]["geometry"]["coordinates"][1]
                    lng = geo_json["features"][index]["geometry"]["coordinates"][0]
                    updated_feature = make_geojson_circle(lat, lng, radius_meters)
                    updated_feature["properties"]["name"] = names[index].strip()
                    updated_feature["properties"]["radius"] = radius_meters
                    geo_json['features'][index] = updated_feature

            elif button_id_dict['type'] == 'remove-point-button':
                index = button_id_dict['index']
                if 0 <= index < len(geo_json['features']):
                    geo_json['features'].pop(index)

        return geo_json

    @app.callback(
        Output("prev-circle-layer", "children"),
        [Input("geo-json-store", "data")],
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
                        radius=radius,
                        color='green', 
                        fill=True, 
                        fillOpacity=0.1
                    )
                )
                circle_layer.append(
                    dl.Marker(
                        position=[lat, lng],
                        children=[dl.Tooltip(content=name)]
                    )
                )
        return circle_layer

    @app.callback(
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
            return html.Div("No Features defined."), [], None

        table_codes = [tc.strip() for tc in table_codes_input.split(',') if tc.strip()]
        if not table_codes:
            return html.Div("No valid table codes provided."), [], None

        final_list = []
        final_block_groups = []

        for feature in geo_json_data['features']:
            if feature['geometry']['type'] != 'Point':
                return html.Div("Invalid GeoJSON data."), [], None

            lng, lat = feature['geometry']['coordinates']
            radius_meters = feature["properties"]['radius']
            point = Point(lng, lat)

            # Figure out correct UTM zone
            utm_epsg = util.get_utm_epsg(lat, lng)

            # Buffer in projected space
            projected_point = gpd.GeoSeries([point], crs=4326).to_crs(epsg=utm_epsg).iloc[0]
            circle = projected_point.buffer(radius_meters)

            # Find intersecting block groups
            query_circle = gpd.GeoSeries([point], crs=4326).to_crs(epsg=utm_epsg).buffer(radius_meters).to_crs(epsg=4326).iloc[0].__geo_interface__
            db_results = util.find_intersecting_features('census-dashboard', 'block-group-geojson', query_circle)
            db_results = [{'geometry': doc['geometry'], **doc['properties']} for doc in db_results]
            db_results = pd.DataFrame(db_results)
            db_results['geometry'] = db_results['geometry'].apply(shape)
            block_group_gdf = gpd.GeoDataFrame(db_results, crs="EPSG:4326")

            # Calculate distance, overlap, etc.
            projected_gdf = block_group_gdf.to_crs(epsg=utm_epsg)
            projected_gdf['distance'] = projected_gdf.centroid.distance(projected_point)

            # Overlap
            projected_circle = gpd.GeoSeries([circle], crs=utm_epsg).to_crs(epsg=4326).iloc[0]
            block_group_gdf['percent_overlap'] = block_group_gdf.geometry.apply(
                lambda geom: geom.intersection(projected_circle).area / geom.area if not geom.is_empty else 0
            )
            block_group_gdf = block_group_gdf[block_group_gdf['percent_overlap'] > 0]

            for table_code in table_codes:
                data_df = cl.aggregate_blockgroups(table_code, block_group_gdf)
                data_df["Value"] = data_df["Value"].apply(lambda x: f"{round(x):,}" if pd.notna(x) else "")
                data_df = data_df[data_df["VarID"].str.endswith("E")]
                data_df['point_name'] = feature['properties']['name']
                final_list.append(data_df)

            final_block_groups.append(block_group_gdf)

        if not final_list:
            return html.Div("No data found for these points/tables."), [], None

        big_df = pd.concat(final_list, ignore_index=True)

        # Pivot
        pivot_df = big_df.pivot_table(
            index='point_name',
            columns='Variable',
            values='Value',
            aggfunc='first'
        ).reset_index()

        # Build data table
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
        final_geo_json = final_block_group_gdf.__geo_interface__

        # Create highlight layer
        highlight_layer = [
            dl.GeoJSON(
                data=feature,
                options=dict(style=dict(color="blue", weight=1, fillOpacity=overlap*0.5)),
            )
            for feature, overlap in zip(final_geo_json["features"], final_block_group_gdf['percent_overlap'])
        ]

        return data_table, highlight_layer, pivot_df.to_dict("records")

    @app.callback(
        Output("download-dataframe-csv", "data"),
        Input("download-button", "n_clicks"),
        State("table-data-storage", "data"),
        prevent_initial_call=True
    )
    def download_data(n_clicks, table_data):
        if not table_data:
            return dash.no_update
        df = pd.DataFrame(table_data)
        return dcc.send_data_frame(df.to_csv, "census_data.csv", index=False)

    @app.callback(
        Output('points-list', 'children'),
        [Input('geo-json-store', 'data')]
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

    @app.callback(
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
