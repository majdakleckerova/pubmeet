from neo4j import GraphDatabase
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import base64
import pandas as pd
load_dotenv()  # Načte proměnné prostředí z .env souboru
neo4j_driver = GraphDatabase.driver(os.getenv('NEO4J_URI'), auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD')))
def close():
    neo4j_driver.close()

file_path = "hospody.xlsx"  # Upravte cestu k souboru
data = pd.read_excel(file_path)
def import_hospody_to_neo4j(data):
    """
    Importuje hospody do Neo4j s ohledem na správné názvy sloupců.
    """
    # Přejmenování sloupců
    data.rename(columns={
        "Název": "name",
        "Adresa": "address",
        "Latitude": "latitude",
        "Longitude": "longitude",
        "Instagram": "instagram"
    }, inplace=True)

    # Kontrola povinných sloupců
    required_columns = ["name", "address", "latitude", "longitude"]
    for col in required_columns:
        if col not in data.columns:
            raise KeyError(f"Chybějící sloupec: {col}")

    query = """
    MERGE (h:Hospital {name: $name})
    ON CREATE SET h.address = $address, 
                  h.latitude = $latitude, 
                  h.longitude = $longitude, 
                  h.instagram = $instagram
    """
    with neo4j_driver.session() as session:
        for _, row in data.iterrows():
            session.run(query, {
                "name": row.get("name", "Neznámé jméno"),
                "address": row.get("address", "Neznámá adresa"),
                "latitude": row.get("latitude", 0.0),
                "longitude": row.get("longitude", 0.0),
                "instagram": row.get("instagram", None)  # Instagram je volitelný
            })
    print("Data byla úspěšně importována.")

import_hospody_to_neo4j(data)

def add_user(username, email, password_hash):
    password_hash_base64 = base64.b64encode(password_hash.encode()).decode()
    with neo4j_driver.session() as session:
        session.run(
            """
            CREATE (u:User {username: $username, email: $email, password_hash: $password_hash})
            """,
            username=username, email=email, password_hash=password_hash_base64
        )
def get_user(username):
    with neo4j_driver.session() as session:
        result = session.run(
            """
            MATCH (u:User {username: $username})
            RETURN u.username AS username, u.password_hash AS password_hash, u.email AS email
            """,
            username=username
        )
        record = result.single()
        if record:
            return {
                "username": record["username"],
                "password_hash": base64.b64decode(record["password_hash"]).decode(),
                "email": record["email"],
            }
        return None
def increment_people_count(pub_name):
    """
    Zvýší počet lidí v hospodě.
    """
    query = """
    MATCH (h:Hospital {name: $name})
    SET h.people_count = COALESCE(h.people_count, 0) + 1
    RETURN h.people_count AS new_count
    """
    with neo4j_driver.session() as session:
        result = session.run(query, name=pub_name)
        record = result.single()
        return record['new_count'] if record else None

def get_pubs():
    """
    Načte seznam všech hospod z databáze Neo4j a odstraní neplatné hodnoty.
    """
    query = """
    MATCH (h:Hospital)
    RETURN h.name AS name, 
           h.address AS address, 
           h.latitude AS latitude, 
           h.longitude AS longitude, 
           COALESCE(h.people_count, 0) AS people_count
    """
    with neo4j_driver.session() as session:
        result = session.run(query)
        pubs = [record.data() for record in result]

        for pub in pubs:
            if pub.get('address') is None or isinstance(pub['address'], float) and pub['address'] != pub['address']:
                pub['address'] = "Neznámá adresa"

            if pub.get('latitude') is None or isinstance(pub['latitude'], float) and pub['latitude'] != pub['latitude']:
                pub['latitude'] = 0.0
            if pub.get('longitude') is None or isinstance(pub['longitude'], float) and pub['longitude'] != pub['longitude']:
                pub['longitude'] = 0.0

        return pubs

def toggle_user_membership(user_id, pub_name):
    """
    Připojení nebo odpojení uživatele k hospodě.
    """
    query_check = """
    MATCH (u:User {id: $user_id})-[:MEMBER_OF]->(h:Hospital)
    RETURN h.name AS current_pub
    """

    query_join = """
    MATCH (u:User {id: $user_id}), (h:Hospital {name: $pub_name})
    MERGE (u)-[:MEMBER_OF]->(h)
    SET h.people_count = COALESCE(h.people_count, 0) + 1
    RETURN h.people_count AS new_count
    """

    query_leave = """
    MATCH (u:User {id: $user_id})-[r:MEMBER_OF]->(h:Hospital {name: $pub_name})
    DELETE r
    SET h.people_count = COALESCE(h.people_count, 1) - 1
    RETURN h.people_count AS new_count
    """

    with neo4j_driver.session() as session:
        # Zjistit, zda je uživatel již členem nějaké hospody
        current_pub = session.run(query_check, user_id=user_id).single()
        if current_pub and current_pub['current_pub'] == pub_name:
            # Odpojit uživatele
            result = session.run(query_leave, user_id=user_id, pub_name=pub_name).single()
            return True, 'left', result['new_count']
        elif current_pub:
            # Uživatel je členem jiné hospody - odmítnout
            return False, 'already_in_other_pub', None
        else:
            # Připojit uživatele k nové hospodě
            result = session.run(query_join, user_id=user_id, pub_name=pub_name).single()
            return True, 'joined', result['new_count']

def toggle_user_hospital(user_id, pub_name):
    """
    Připojí uživatele k hospodě nebo ho odpojí, pokud je již členem.
    """
    query = """
    MATCH (u:User {id: $user_id})
    MATCH (h:Hospital {name: $pub_name})
    OPTIONAL MATCH (u)-[r:VISITS]->(h)
    WITH u, h, r, CASE WHEN r IS NULL THEN 1 ELSE -1 END AS change
    MERGE (u)-[:VISITS]->(h) DELETE r
    SET h.people_count = COALESCE(h.people_count, 0) + change
    RETURN h.people_count AS new_count, change > 0 AS joined
    """
    with neo4j_driver.session() as session:
        result = session.run(query, user_id=user_id, pub_name=pub_name).single()
        return "joined" if result["joined"] else "left", result["new_count"]
def update_session(user_id):
    """
    Aktualizuje platnost session pro uživatele v Neo4j.
    """
    expiration_time = datetime.utcnow() + timedelta(hours=1)
    with neo4j_driver.session() as session:
        session.run(
            """
            MATCH (u:User {id: $user_id})
            SET u.session_expiration = $expiration_time
            """,
            user_id=user_id,
            expiration_time=expiration_time.isoformat()
        )

def validate_session(user_id):
    """
    Ověří, zda session uživatele v Neo4j není expirovaná.
    """
    with neo4j_driver.session() as session:
        result = session.run(
            """
            MATCH (u:User {id: $user_id})
            RETURN u.session_expiration AS session_expiration
            """,
            user_id=user_id
        )
        record = result.single()
        if record and record["session_expiration"]:
            expiration_time = datetime.fromisoformat(record["session_expiration"])
            return expiration_time > datetime.utcnow()
        return False