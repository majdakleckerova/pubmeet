from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

load_dotenv()

neo4j_driver = GraphDatabase.driver(
    os.getenv('NEO4J_URI'),
    auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD'))
)

def get_neo4j_session():
    return neo4j_driver.session()