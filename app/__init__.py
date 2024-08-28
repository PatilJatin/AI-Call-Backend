from flask import Flask

app = Flask(__name__)

# Import routes after initializing the Flask app to avoid circular import
from app import route
