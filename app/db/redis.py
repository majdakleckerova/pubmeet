import redis
import os
import base64
import json
redis_client = redis.StrictRedis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=int(os.getenv("REDIS_DB", 0)),
    decode_responses=True  # Zajistí dekódování jako UTF-8
)

def cache_user_session(session_id, data, expiration=3600):
    """
    Uloží data session do Redis s kódováním UTF-8.
    """
    if isinstance(data, dict):
        data = json.dumps(data)  # Převést na JSON, pokud je to slovník
    redis_client.setex(f"session:{session_id}", expiration, data.encode('utf-8'))
def get_user_session(session_id):
    """
    Načte data session z Redis a dekóduje je.
    """
    session_data = redis_client.get(f"session:{session_id}")
    if session_data:
        try:
            # Pokud jsou data v bytes, dekódujeme je, jinak použijeme přímo
            if isinstance(session_data, bytes):
                session_data = session_data.decode('utf-8')  # Dekódovat UTF-8
            return json.loads(session_data)  # Převést JSON zpět na slovník
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            print(f"Chyba při dekódování session: {e}")
            return None  # Pokud dekódování selže, vrátíme None
    return None
def delete_user_session(session_id):
    """
    Smaže data session z Redis podle session_id.
    """
    redis_client.delete(f"session:{session_id}")
