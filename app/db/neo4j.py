from neo4j import GraphDatabase
import os
from dotenv import load_dotenv
load_dotenv()  # Načte proměnné prostředí z .env souboru

neo4j_driver = GraphDatabase.driver(os.getenv('NEO4J_URI'), auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD')))
def close():
    neo4j_driver.close()

def add_user(username, email, password_hash):
    with neo4j_driver.session() as session:
        session.run(
            """
            CREATE (u:User {username: $username, email: $email, password_hash: $password_hash})
            """,
            username=username, email=email, password_hash=password_hash
        )

def get_user(username):
    with neo4j_driver.session() as session:
        result = session.run(
            "MATCH (u:User {username: $username}) RETURN u.username AS username, u.password_hash AS password_hash, u.email AS email",
            username=username
        )
        return result.single() if result else None
