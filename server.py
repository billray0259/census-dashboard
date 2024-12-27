# server.py
from flask import Flask
from census_dashboard import create_dash_app

server = Flask(__name__)

# Create the Dash app by passing in the Flask server
app = create_dash_app(server, url_base_pathname="/")

if __name__ == "__main__":
    server.run(debug=True)
