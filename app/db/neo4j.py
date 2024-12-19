from neo4j import GraphDatabase
from dotenv import load_dotenv
import os
import pandas as pd

from flask import Blueprint, jsonify, request
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


@neo4j_bp.route('/send_friend_request', methods=['POST'])
def send_friend_request():
    if not current_user.is_authenticated:
        return jsonify({"error": "Přihlaste se, prosím, abyste mohli poslat žádost o přátelství."}), 401

    data = request.json
    username2 = data.get("username2")

    if not username2:
        return jsonify({"error": "Chybí username přítele."}), 400

    username1 = current_user.username

    with neo4j_driver.session() as session:
        # Vytvoří žádost o přátelství
        query = """
        MATCH (u1:User {username: $username1}), (u2:User {username: $username2})
        MERGE (u1)-[r:FRIEND_REQUEST {status: 'REQUESTED'}]->(u2)
        RETURN u1, u2, r
        """
        result = session.run(query, username1=username1, username2=username2)
        if result.peek() is None:
            return jsonify({"error": "Uživatelé nebyli nalezeni."}), 404
        return jsonify({"message": f"Žádost o přátelství byla odeslána uživateli {username2}."}), 200

@neo4j_bp.route('/accept_friend_request', methods=['POST'])
def accept_friend_request():
    if not current_user.is_authenticated:
        return jsonify({"error": "Přihlaste se, prosím, abyste mohli potvrdit žádost o přátelství."}), 401

    data = request.json
    username1 = data.get("username1")  # Odesílatel žádosti

    if not username1:
        return jsonify({"error": "Chybí username odesílatele žádosti."}), 400

    username2 = current_user.username

    with neo4j_driver.session() as session:
        # Potvrzení žádosti o přátelství
        query = """
        MATCH (u1:User {username: $username1})-[r:FRIEND_REQUEST {status: 'REQUESTED'}]->(u2:User {username: $username2})
        SET r.status = 'CONFIRMED'
        MERGE (u2)-[:FRIEND]->(u1)
        RETURN u1, u2, r
        """
        result = session.run(query, username1=username1, username2=username2)
        if result.peek() is None:
            return jsonify({"error": "Žádost o přátelství nebyla nalezena."}), 404
        return jsonify({"message": f"Přátelství mezi {username1} a {username2} bylo potvrzeno."}), 200

@neo4j_bp.route('/handle_friend_request', methods=['POST'])
def handle_friend_request():
    if not current_user.is_authenticated:
        return jsonify({"error": "Přihlaste se, prosím."}), 401

    data = request.json
    username = data.get('username')
    action = data.get('action')

    if not username or not action:
        return jsonify({"error": "Chybí údaje o uživatelském jménu nebo akci."}), 400

    if action not in ['accept', 'reject']:
        return jsonify({"error": "Neplatná akce."}), 400

    with neo4j_driver.session() as session:
        if action == 'accept':
            # Změna statusu žádosti na 'CONFIRMED' a vytvoření přátelského vztahu
            query = """
            MATCH (u1:User {username: $username1})-[r:FRIEND_REQUEST {status: 'REQUESTED'}]->(u2:User {username: $username2})
            SET r.status = 'CONFIRMED'
            MERGE (u2)-[:FRIEND]->(u1)
            RETURN u1, u2, r
            """
            result = session.run(query, username1=username, username2=current_user.username)
        elif action == 'reject':
            # Odstranění žádosti o přátelství
            query = """
            MATCH (u1:User {username: $username1})-[r:FRIEND_REQUEST {status: 'REQUESTED'}]->(u2:User {username: $username2})
            DELETE r
            """
            result = session.run(query, username1=username, username2=current_user.username)

    return jsonify({"success": True, "message": f"Akce {action} byla úspěšně provedena."})
