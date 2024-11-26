from flask import Blueprint, jsonify, request
from app.db.redis import redis_client
from app.extensions import socketio
import os
map_bp = Blueprint('map', __name__)
import pandas as pd

def load_pubs_from_excel():
    file_path = "hospody.xlsx"
    hospody_df = pd.read_excel(file_path)
    hospody_df = hospody_df.dropna(subset=['Latitude', 'Longitude'])  # Odstranění záznamů bez souřadnic
    return hospody_df.to_dict(orient='records')
# Endpoint pro načtení hospod
@map_bp.route('/get_pubs', methods=['GET'])
def get_pubs():
    hospody = load_pubs_from_excel()
    response = []
    for hospoda in hospody:
        name = hospoda["Název"]
        latitude = hospoda["Latitude"]
        longitude = hospoda["Longitude"]
        redis_key = f"pub:{name.replace(' ', '_')}:users"

        # Získání počtu uživatelů z Redis
        if redis_client.exists(redis_key):
            people_count = redis_client.llen(redis_key)
        else:
            # Pokud klíč neexistuje, nastav prázdný seznam
            redis_client.delete(redis_key)  # Pro jistotu smaž zbytky
            people_count = 0

        response.append({
            "name": name,
            "latitude": latitude,
            "longitude": longitude,
            "people_count": people_count
        })
    return jsonify(response)
# Endpoint pro připojení/odpojení od hospody
@map_bp.route('/toggle_pub', methods=['POST'])
def toggle_pub():
    data = request.json
    pub_name = data.get('name')  # Name of the pub user interacts with
    username = data.get('username')  # Username of the current user
    redis_user_key = f"user:{username}:current_pub"  # Key to track user's current pub
    redis_pub_key = f"pub:{pub_name.replace(' ', '_')}:users"  # Key to track pub's users

    # Fetch the user's current pub from Redis
    current_pub = redis_client.get(redis_user_key)

    if current_pub == pub_name:
        # User is explicitly leaving the current pub
        users_in_pub = redis_client.lrange(redis_pub_key, 0, -1)
        if username in users_in_pub:
            users_in_pub.remove(username)  # Remove user from the local list
            redis_client.delete(redis_pub_key)
            if users_in_pub:
                redis_client.rpush(redis_pub_key, *users_in_pub)  # Update Redis with the new list

        redis_client.delete(redis_user_key)  # Clear the user's current pub association
        action = "left"
    else:
        # User is joining a new pub
        if current_pub:
            # Handle leaving the previous pub
            old_pub_key = f"pub:{current_pub.replace(' ', '_')}:users"
            old_users = redis_client.lrange(old_pub_key, 0, -1)
            if username in old_users:
                old_users.remove(username)
                redis_client.delete(old_pub_key)
                if old_users:
                    redis_client.rpush(old_pub_key, *old_users)  # Update Redis for the old pub

        # Join the new pub
        users_in_pub = redis_client.lrange(redis_pub_key, 0, -1)
        if username not in users_in_pub:
            users_in_pub.append(username)
            redis_client.delete(redis_pub_key)
            redis_client.rpush(redis_pub_key, *users_in_pub)

        redis_client.set(redis_user_key, pub_name)  # Update user's current pub
        action = "joined"

    # Calculate new counts for the updated pub
    new_count = len(users_in_pub)

    # Emit real-time updates for the current pub
    socketio.emit('update_pub_count', {'pub_name': pub_name, 'new_count': new_count})
    
    # Emit updates for the old pub if applicable
    if current_pub and current_pub != pub_name:
        old_pub_count = redis_client.llen(f"pub:{current_pub.replace(' ', '_')}:users")
        socketio.emit('update_pub_count', {'pub_name': current_pub, 'new_count': old_pub_count})

    return jsonify({"success": True, "action": action, "new_count": new_count})
