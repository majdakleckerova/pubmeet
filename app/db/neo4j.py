from neo4j import GraphDatabase
from dotenv import load_dotenv
from flask import Blueprint, jsonify, request
from flask_login import current_user
import os
import pandas as pd

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
        hospody_df = pd.read_excel(file_path).dropna(subset=["Latitude", "Longitude", "Adresa"])
    except Exception as e:
        return f"Chyba při načítání Excelu: {e}"

    with neo4j_driver.session() as session:
        for _, row in hospody_df.iterrows():
            try:
                session.run(
                    """
                    MERGE (p:Pub {name: $name})
                    SET p.latitude = $latitude, p.longitude = $longitude, p.address = $address
                    """,
                    name=row["Název"], 
                    latitude=row["Latitude"], 
                    longitude=row["Longitude"],
                    address=row["Adresa"]
                )
            except Exception as e:
                print(f"Chyba při zapisování hospody {row['Název']}: {e}")
                continue

    return "Hospody byly úspěšně zapsány do Neo4j."

result = load_pubs_to_neo4j("hospody.xlsx")
result

def get_users():
    with neo4j_driver.session() as session:
        result = session.run("MATCH (u:User) RETURN u.username AS username, u.email AS email, u.id AS id, u.profile_photo AS profile_photo, u.bio AS bio, u.birthdate AS birthdate, u.favourite_drink AS favourite_drink, u.nickname AS nickname")
        return result.data()
    
def get_friends(user_id):
    with neo4j_driver.session() as session:
        result = session.run("""
            MATCH (u:User {id: $user_id})-[:FRIEND]->(f:User)
            RETURN f.username AS username, f.email AS email, f.id AS id, f.profile_photo AS profile_photo
        """, user_id=user_id)
        return result.data()
    

#############################################################################################################################
# Žádosti o přátelství
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
        query = """
        MATCH (u1:User {username: $username1}), (u2:User {username: $username2})
        OPTIONAL MATCH (u1)-[r1:FRIEND_REQUEST]->(u2)
        OPTIONAL MATCH (u2)-[r2:FRIEND_REQUEST]->(u1)
        OPTIONAL MATCH (u1)-[r3:FRIEND]->(u2)
        OPTIONAL MATCH (u2)-[r4:FRIEND]->(u1)
        RETURN COUNT(r1) + COUNT(r2) + COUNT(r3) + COUNT(r4) > 0 AS relationship_exists
        """
        result = session.run(query, username1=username1, username2=username2)
        relationship_exists = result.single()[0]

        if relationship_exists:
            return jsonify({"error": "Mezi tebou a tímto uživatelem již existuje žádost o přátelství nebo přátelství."}), 400

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
        # Nejprve zkontrolujeme, zda žádost o přátelství existuje
        query = """
        MATCH (u1:User {username: $username1})-[r:FRIEND_REQUEST {status: 'REQUESTED'}]->(u2:User {username: $username2})
        RETURN COUNT(r) > 0 AS exists_request
        """
        result = session.run(query, username1=username1, username2=username2)
        request_exists = result.single()[0]

        if not request_exists:
            return jsonify({"error": "Žádost o přátelství nebyla nalezena."}), 404

        # Potvrďte žádost a vytvořte vztah FRIENDS
        query = """
        MATCH (u1:User {username: $username1})-[r:FRIEND_REQUEST {status: 'REQUESTED'}]->(u2:User {username: $username2})
        SET r.status = 'CONFIRMED'
        MERGE (u2)-[:FRIEND]->(u1)
        RETURN u1, u2, r
        """
        result = session.run(query, username1=username1, username2=username2)

        query_delete_request = """
        MATCH (u1:User {username: $username1})-[r:FRIEND_REQUEST {status: 'REQUESTED'}]->(u2:User {username: $username2})
        DELETE r
        """
        session.run(query_delete_request, username1=username1, username2=username2)


        if result.peek() is None:
            return jsonify({"error": "Chyba při potvrzování přátelství."}), 500
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
            # Zkontrolujeme, jestli už mezi uživateli neexistuje přátelství
            query = """
            MATCH (u1:User {username: $username1})-[r:FRIEND_REQUEST {status: 'REQUESTED'}]->(u2:User {username: $username2})
            RETURN COUNT(r) > 0 AS exists_request
            """
            result = session.run(query, username1=username, username2=current_user.username)
            request_exists = result.single()[0]

            if not request_exists:
                return jsonify({"error": "Žádost o přátelství nebyla nalezena."}), 404

            # Potvrzení žádosti a vytvoření přátelského vztahu
            query = """
            MATCH (u1:User {username: $username1})-[r:FRIEND_REQUEST {status: 'REQUESTED'}]->(u2:User {username: $username2})
            SET r.status = 'CONFIRMED'
            MERGE (u2)-[:FRIEND]->(u1)
            RETURN u1, u2, r
            """
            result = session.run(query, username1=username, username2=current_user.username)
        elif action == 'reject':
            # Zkontrolujeme, zda žádost o přátelství existuje, pokud ano, odstraníme ji
            query = """
            MATCH (u1:User {username: $username1})-[r:FRIEND_REQUEST {status: 'REQUESTED'}]->(u2:User {username: $username2})
            RETURN COUNT(r) > 0 AS exists_request
            """
            result = session.run(query, username1=username, username2=current_user.username)
            request_exists = result.single()[0]

            if not request_exists:
                return jsonify({"error": "Žádost o přátelství nebyla nalezena."}), 404

            # Odstraníme žádost o přátelství
            query = """
            MATCH (u1:User {username: $username1})-[r:FRIEND_REQUEST {status: 'REQUESTED'}]->(u2:User {username: $username2})
            DELETE r
            """
            result = session.run(query, username1=username, username2=current_user.username)

    return jsonify({"success": True, "message": f"Akce {action} byla úspěšně provedena."})

def get_friendship_status(current_user, target_user):
    with neo4j_driver.session() as session:
        query = """
        MATCH (u1:User {username: $current_user}), (u2:User {username: $target_user})
        OPTIONAL MATCH (u1)-[r1:FRIEND_REQUEST]->(u2)
        OPTIONAL MATCH (u2)-[r2:FRIEND_REQUEST]->(u1)
        OPTIONAL MATCH (u1)-[r3:FRIEND]->(u2)
        OPTIONAL MATCH (u2)-[r4:FRIEND]->(u1)
        OPTIONAL MATCH (u1)-[r5:FRIEND_REQUEST {status: 'CONFIRMED'}]->(u2)
        OPTIONAL MATCH (u2)-[r6:FRIEND_REQUEST {status: 'CONFIRMED'}]->(u1)
        RETURN
            COUNT(r1) > 0 AS sent_request,
            COUNT(r2) > 0 AS received_request,
            COUNT(r3) > 0 AS are_friends,
            COUNT(r5) > 0 OR COUNT(r6) > 0 AS are_friends_confirmed
        """
        result = session.run(query, current_user=current_user, target_user=target_user)
        data = result.single()
        
        if data:
            if data['are_friends'] or data['are_friends_confirmed']:
                return 'friends'  # Jsou přátelé (i když byla žádost potvrzena)
            elif data['sent_request']:
                return 'sent_request'  # Žádost odeslána
            elif data['received_request']:
                return 'received_request'  # Žádost přijmout
            else:
                return 'no_relationship'  # Žádný vztah
        return 'no_relationship'  # Žádný vztah
