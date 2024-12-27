# dash_app/app.py

import dash
import dash_bootstrap_components as dbc
from flask import Flask

import census_dashboard as cd

def create_dash_app(server: Flask, url_base_pathname: str = "/"):
    """
    Factory function to create a Dash application.
    """
    app = dash.Dash(
        __name__,
        server=server,
        url_base_pathname=url_base_pathname,
        external_stylesheets=[dbc.themes.SPACELAB],
    )

    # Set the layout
    app.layout = cd.create_layout()

    # Register all callbacks
    cd.register_callbacks(app)

    return app
