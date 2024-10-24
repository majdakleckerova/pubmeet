from flask import Flask
from pymongo import MongoClient
import redis
from neo4j import GraphDatabase
import os
from flask_login import LoginManager
from app.models.user import User

app = Flask(__name__)
app.secret_key = ''
# MongoDB connection
mongo_client = MongoClient(os.getenv('MONGODB_URI'))
db = mongo_client['pubMeet']

# Redis connection
redis_client = redis.StrictRedis(host=os.getenv('REDIS_HOST'), port=os.getenv('REDIS_PORT'))

# Neo4j connection
neo4j_driver = GraphDatabase.driver(os.getenv('NEO4J_URI'), auth=(os.getenv('pubMeet'), os.getenv('heslo')))
# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Přesměrování na login stránku, pokud uživatel není přihlášen

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)
from app import routes
