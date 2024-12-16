from neo4j import GraphDatabase
from dotenv import load_dotenv
import os
import pandas as pd

from flask import Blueprint, jsonify
from flask_login import current_user
load_dotenv()

neo4j_bp = Blueprint('neo4j', __name__)

neo4j_driver = GraphDatabase.driver(
    os.getenv('NEO4J_URI'),
    auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD'))
)

def get_neo4j_session():
    return neo4j_driver.session()
# Funkce pro zapsání hospod do Neo4j
def load_pubs_to_neo4j(file_path="hospody.xlsx"):
    try:
        # Načtení dat z Excelu
        hospody_df = pd.read_excel(file_path).dropna(subset=["Latitude", "Longitude"])
    except Exception as e:
        return f"Chyba při načítání Excelu: {e}"

    with neo4j_driver.session() as session:
        for _, row in hospody_df.iterrows():
            try:
                session.run(
                    """
                    MERGE (p:Pub {name: $name})
                    SET p.latitude = $latitude, p.longitude = $longitude
                    """,
                    name=row["Název"], latitude=row["Latitude"], longitude=row["Longitude"]
                )
            except Exception as e:
                print(f"Chyba při zapisování hospody {row['Název']}: {e}")
                continue

    return "Hospody byly úspěšně zapsány do Neo4j."

## Spuštění funkce
result = load_pubs_to_neo4j("hospody.xlsx")
result

def get_users():
    with neo4j_driver.session() as session:
        result = session.run("MATCH (u:User) RETURN u.username AS username, u.email AS email, u.id AS id")
        return result.data()
    
#def get_user_by_id(user_id):
#    with neo4j_driver.session() as session:
#        result = session.run("MATCH (u:User {id: $id}) RETURN u", id=user_id)
#        user = result.single()
#        return user['u'] if user else None


# Funkce pro získání lajknutých hospod uživatelem

