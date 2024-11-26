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
    pub_name = data.get('name')
    username = data.get('username')  # Aktuální uživatel
    redis_user_key = f"user:{username}:current_pub"
    redis_pub_key = f"pub:{pub_name.replace(' ', '_')}:users"

    # Zjisti, zda je uživatel již připojen k jiné hospodě
    current_pub = redis_client.get(redis_user_key)

    if current_pub:
        # Uživatel je připojen k jiné hospodě, odpoj ho
        old_pub_key = f"pub:{current_pub.replace(' ', '_')}:users"
        redis_client.lrem(old_pub_key, 0, username)  # Odebrání uživatele ze staré hospody

    if current_pub == pub_name:
        # Pokud uživatel opouští stejnou hospodu
        redis_client.lrem(redis_pub_key, 0, username)
        if redis_client.llen(redis_pub_key) == 0:
            redis_client.delete(redis_pub_key)  # Smaž klíč pouze pokud je prázdný
        redis_client.delete(redis_user_key)
        action = "left"
    else:
        # Připojení k nové hospodě
        redis_client.lpush(redis_pub_key, username)  # Přidání uživatele do nové hospody
        redis_client.set(redis_user_key, pub_name)  # Aktualizuj aktuální hospodu uživatele
        action = "joined"

    # Aktualizace počtu lidí v nové hospodě
    new_count = redis_client.llen(redis_pub_key)

    # Real-time update přes Socket.IO
    socketio.emit('update_pub_count', {'pub_name': pub_name, 'new_count': new_count})
    if current_pub:
        # Aktualizuj starou hospodu (počet lidí)
        old_pub_count = redis_client.llen(old_pub_key)
        socketio.emit('update_pub_count', {'pub_name': current_pub, 'new_count': old_pub_count})

    return jsonify({"success": True, "action": action, "new_count": new_count})
