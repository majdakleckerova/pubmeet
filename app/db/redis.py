import redis
import os

# Připojení k Redis
redis_client = redis.StrictRedis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=0,
    decode_responses=True
)

def cache_user_session(user_id, data, expiration=3600):
    redis_client.setex(f"user_session:{user_id}", expiration, data)

def get_user_session(user_id):
    return redis_client.get(f"user_session:{user_id}")

def delete_user_session(user_id):
    redis_client.delete(f"user_session:{user_id}")
