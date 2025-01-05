from flask import Blueprint, jsonify, request
from app.db.redis import redis_client
from flask_login import current_user
from app.extensions import socketio
from app.db.neo4j import neo4j_driver
import os
map_bp = Blueprint('map', __name__)
import pandas as pd
from app.db.neo4j import get_neo4j_session
from flask_login import current_user
# Endpoint pro načtení hospod
@map_bp.route('/get_pubs', methods=['GET'])
def get_pubs():
    current_username = current_user.username if current_user.is_authenticated else None
    with get_neo4j_session() as session:
        result = session.run("""
            MATCH (p:Pub)
            OPTIONAL MATCH (p)<-[:IN_PUB]-(u:User)
            OPTIONAL MATCH (p)<-[:LIKES]-(l:User)
            OPTIONAL MATCH (u:User {username: $username})-[:VISITS]->(p)
            RETURN p.name AS name, p.latitude AS latitude, p.longitude AS longitude, 
                   p.address AS address, COUNT(u) AS users_count, COUNT(l) AS likes_count,
                   CASE WHEN COUNT(u) > 0 THEN true ELSE false END AS is_connected
        """, username=current_username)
        pubs = []
        for record in result:
            pubs.append({
                "name": record["name"],
                "latitude": record["latitude"],
                "longitude": record["longitude"],
                "address": record["address"],
                "people_count": record["users_count"],
                "likes_count": record["likes_count"],
                "is_connected": record["is_connected"]  # Přidáme informaci o připojení
            })
        return jsonify(pubs)
# Endpoint pro přepočítání počtu lidí v hospodě
@map_bp.route('/get_pub_count', methods=['POST'])
def get_pub_count():
    try:
        data = request.json
        pub_name = data['name']
        
        with neo4j_driver.session() as session:
            result = session.run("""
                MATCH (p:Pub {name: $pub_name})
                OPTIONAL MATCH (p)<-[:VISITS]-(u:User)
                RETURN COUNT(u) AS user_count
            """, pub_name=pub_name)
            count = result.single()["user_count"]

        return jsonify(success=True, pub_name=pub_name, user_count=count)
    except Exception as e:
        print(f"Error in get_pub_count: {e}")
        return jsonify(success=False, error="An error occurred"), 500

# Endpoint pro připojení/odpojení od hospody
@map_bp.route('/toggle_pub', methods=['POST'])
def toggle_pub():
    try:
        print("Received toggle_pub request")
        data = request.json
        pub_name = data['name']
        print(f"Pub name: {pub_name}")
        data = request.json
        pub_name = data['name']
    
        # Ověření, že uživatel je přihlášen
        if not current_user.is_authenticated:
            return jsonify(success=False, message="User not authenticated"), 401
    
        username = current_user.username
    
        with neo4j_driver.session() as session:
            # Zjisti, zda je uživatel připojen do nějaké hospody
            current_relationship = session.run("""
                MATCH (u:User {username: $username})-[r:VISITS]->(p:Pub)
                RETURN p.name AS current_pub
            """, username=username).single()
    
            if current_relationship:
                current_pub = current_relationship["current_pub"]
                # Pokud uživatel je připojen k jiné hospodě, odpoj jej
                if current_pub != pub_name:
                    session.run("""
                        MATCH (u:User {username: $username})-[r:VISITS]->(p:Pub {name: $current_pub})
                        DELETE r
                    """, username=username, current_pub=current_pub)
                    action = 'switched'
                else:
                    # Pokud uživatel klikne na stejnou hospodu, odpojí se
                    session.run("""
                        MATCH (u:User {username: $username})-[r:VISITS]->(p:Pub {name: $pub_name})
                        DELETE r
                    """, username=username, pub_name=pub_name)
                    action = 'left'
            else:
                # Pokud není připojen, přidej vztah
                session.run("""
                    MATCH (u:User {username: $username}), (p:Pub {name: $pub_name})
                    CREATE (u)-[r:VISITS]->(p)
                """, username=username, pub_name=pub_name)
                action = 'joined'
    
            # Vždy přepočítej počet lidí v hospodě
            result = session.run("""
                MATCH (p:Pub {name: $pub_name})
                OPTIONAL MATCH (p)<-[:VISITS]-(u:User)
                WITH p, COUNT(u) AS user_count
                SET p.people_count = user_count
                RETURN p.people_count AS people_count
            """, pub_name=pub_name)
            new_count = result.single()["people_count"]
        # Emituj real-time aktualizaci
        socketio.emit('update_pub_count', {
            'pub_name': pub_name,
            'new_count': new_count
        })
    
        return jsonify(success=True, action=action, new_count=new_count)
    except Exception as e:
        print(f"Error in toggle_pub: {e}")
        return jsonify(success=False, error="An error occurred"), 500
    
# Endpoint pro přidání/odebrání like u hospody
@map_bp.route('/toggle_like', methods=['POST'])
def toggle_like():
    try:
        if not current_user.is_authenticated:
            return jsonify(success=False, message="User not authenticated"), 401

        data = request.json
        pub_name = data['name']
        username = current_user.username

        with neo4j_driver.session() as session:
            # Zkontroluj, zda uživatel již dává like této hospodě
            existing_like = session.run("""
                MATCH (u:User {username: $username})-[r:LIKES]->(p:Pub {name: $pub_name})
                RETURN r
            """, username=username, pub_name=pub_name).single()

            if existing_like:
                # Pokud uživatel již like dal, odebereme ho
                session.run("""
                    MATCH (u:User {username: $username})-[r:LIKES]->(p:Pub {name: $pub_name})
                    DELETE r
                """, username=username, pub_name=pub_name)
                action = 'unliked'
            else:
                # Pokud uživatel ještě like nedal, přidáme ho
                session.run("""
                    MATCH (u:User {username: $username}), (p:Pub {name: $pub_name})
                    CREATE (u)-[r:LIKES]->(p)
                """, username=username, pub_name=pub_name)
                action = 'liked'

            # Po změně like přepočítáme počet lajků pro tuto hospodu
            result = session.run("""
                MATCH (p:Pub {name: $pub_name})
                OPTIONAL MATCH (p)<-[:LIKES]-(l:User)
                RETURN COUNT(l) AS likes_count
            """, pub_name=pub_name)
            new_like_count = result.single()["likes_count"]

            # Emituj real-time aktualizaci lajků pro tuto hospodu
            socketio.emit('update_like_count', {
                'pub_name': pub_name,
                'new_like_count': new_like_count
            })

        return jsonify(success=True, action=action)
    except Exception as e:
        print(f"Error in toggle_like: {e}")
        return jsonify(success=False, error="An error occurred"), 500
    

@map_bp.route('/get_liked_pubs', methods=['GET'])
def get_liked_pubs():
    if current_user.is_authenticated:
        username = current_user.username
        try:
            with neo4j_driver.session() as session:
                # Dotaz na lajknuté hospody
                result = session.run("""
                    MATCH (u:User {username: $username})-[:LIKES]->(p:Pub)
                    RETURN p.name AS pub_name
                """, username=username)
                liked_pubs = [record["pub_name"] for record in result]
            return jsonify(success=True, pubs=liked_pubs)
        except Exception as e:
            print(f"Error in get_liked_pubs: {e}")
            return jsonify(success=False, error="Error fetching liked pubs"), 500
    return jsonify(success=False, message="User not authenticated"), 401




@map_bp.route('/get_pub_visitors', methods=['POST'])
def get_pub_visitors():
    try:
        data = request.json
        pub_name = data['name']
        with neo4j_driver.session() as session:
            result = session.run("""
                MATCH (p:Pub {name: $pub_name})<-[:VISITS]-(u:User)
                RETURN u.username AS username, u.profile_photo AS profile_picture
            """, pub_name=pub_name)
            visitors = [{"username": record["username"], "profile_picture": record["profile_picture"]} for record in result]
        return jsonify(success=True, visitors=visitors)
    except Exception as e:
        print(f"Error in get_pub_visitors: {e}")
        return jsonify(success=False, error="An error occurred"), 500
@map_bp.route('/get_like_count', methods=['POST'])
def get_like_count():
    if not current_user.is_authenticated:
        return jsonify(success=False, error="User not authenticated"), 401

    data = request.json
    pub_name = data.get('name')

    try:
        with get_neo4j_session() as session:
            result = session.run("""
                MATCH (p:Pub {name: $pub_name})
                OPTIONAL MATCH (p)<-[:LIKES]-(u:User)
                RETURN COUNT(u) AS like_count
            """, pub_name=pub_name)
            like_count = result.single()["like_count"]
            return jsonify(success=True, like_count=like_count)
    except Exception as e:
        print(f"Error in get_like_count: {e}")
        return jsonify(success=False, error="An error occurred"), 500

@map_bp.route('/is_user_in_pub', methods=['POST'])
def is_user_in_pub():
    if not current_user.is_authenticated:
        return jsonify(success=False, error="User not authenticated"), 401

    data = request.json
    pub_name = data.get('name')

    try:
        with get_neo4j_session() as session:
            result = session.run("""
                MATCH (u:User {username: $username})-[r:VISITS]->(p:Pub {name: $pub_name})
                RETURN COUNT(r) > 0 AS is_connected
            """, username=current_user.username, pub_name=pub_name)
            is_connected = result.single()["is_connected"]
            return jsonify(success=True, is_connected=is_connected)
    except Exception as e:
        print(f"Error in is_user_in_pub: {e}")
        return jsonify(success=False, error="An error occurred"), 500

@map_bp.route('/get_pub_details', methods=['POST'])
def get_pub_details():
    if not current_user.is_authenticated:
        return jsonify(success=False, error="User not authenticated"), 401

    data = request.json
    pub_name = data.get('name')

    try:
        with get_neo4j_session() as session:
            result = session.run("""
                MATCH (p:Pub {name: $pub_name})
                OPTIONAL MATCH (p)<-[:VISITS]-(u:User)
                OPTIONAL MATCH (p)<-[:LIKES]-(l:User)
                RETURN COUNT(u) AS people_count, COUNT(l) AS like_count
            """, pub_name=pub_name)
            record = result.single()
            return jsonify(success=True, 
                           people_count=record["people_count"], 
                           like_count=record["like_count"])
    except Exception as e:
        print(f"Error in get_pub_details: {e}")
        return jsonify(success=False, error="An error occurred"), 500
@map_bp.route('/is_pub_liked', methods=['POST'])
def is_pub_liked():
    if not current_user.is_authenticated:
        return jsonify(success=False, error="User not authenticated"), 401

    data = request.json
    pub_name = data.get('name')

    try:
        with get_neo4j_session() as session:
            result = session.run("""
                MATCH (u:User {username: $username})-[r:LIKES]->(p:Pub {name: $pub_name})
                RETURN COUNT(r) > 0 AS is_liked
            """, username=current_user.username, pub_name=pub_name)
            is_liked = result.single()["is_liked"]
            return jsonify(success=True, is_liked=is_liked)
    except Exception as e:
        print(f"Error in is_pub_liked: {e}")
        return jsonify(success=False, error="An error occurred"), 500
@map_bp.route('/get_current_pub', methods=['GET'])
def get_current_pub():
    if not current_user.is_authenticated:
        return jsonify(success=False, message="User not authenticated"), 401

    try:
        with get_neo4j_session() as session:
            result = session.run("""
                MATCH (u:User {username: $username})-[r:VISITS]->(p:Pub)
                RETURN p.name AS current_pub
            """, username=current_user.username)
            record = result.single()
            current_pub = record["current_pub"] if record else None

        return jsonify(success=True, current_pub=current_pub)
    except Exception as e:
        print(f"Error in get_current_pub: {e}")
        return jsonify(success=False, error="An error occurred"), 500
