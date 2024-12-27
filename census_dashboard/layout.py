# dash_app/layout.py

import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table
import dash_leaflet as dl

# Any constants or placeholders can go here, e.g.
DEFAULT_RADIUS = 5 * 1609.34
BLANK_GEOJSON = {
    "type": "FeatureCollection",
    "features": []
}

def create_layout():
    """
    Returns the main Dash layout (the root container).
    """
    return dbc.Container(
        [
            dbc.Row(
                dbc.Col(
                    html.H1("Census Dashboard", className="text-center"),
                    width=12
                )
            ),
            dbc.Row(
                dbc.Col(
                    [
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
                                                html.Li("Click 'Download Data' to export the results table as a csv file."),
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
                    # Left sidebar card
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
                                            style={'width': '70%'}
                                        ),
                                        dbc.Input(
                                            id='radius-input',
                                            type='number',
                                            min=0.1,
                                            value=5,
                                            style={'width': '10%'}
                                        ),
                                        dbc.Select(
                                            id='unit-toggle',
                                            options=[
                                                {'label': 'Miles', 'value': 'miles'},
                                                {'label': 'Kilometers', 'value': 'km'}
                                            ],
                                            value='miles',
                                            style={'width': '20%'}
                                        )
                                    ],
                                    className="d-flex align-items-center mt-3"
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
                        center={'lat': 40, 'lng': -100},
                        zoom=4,
                        children=[
                            dl.TileLayer(),
                            dl.LayerGroup(id="circle-layer"),
                            dl.LayerGroup(id="prev-circle-layer"),
                            dl.LayerGroup(id="highlight-layer")
                        ],
                        id="map",
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
                        row_selectable='multi',
                        selected_rows=[]
                    )),
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
                    dcc.Loading(html.Div(id="data-table", className="text-center")),
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
            dcc.Store(id="state-storage"),
            dcc.Store(id="table-data-storage"),
            dcc.Store(id="geo-json-store", data=BLANK_GEOJSON),
            dcc.Store(id="search-output"),
        ],
        fluid=True,
    )
