from flask import Flask
from flask_login import LoginManager
from dotenv import load_dotenv
import os
from app.db.neo4j import get_user, neo4j_driver
from app.db.redis import redis_client
from app.models.user import User
import uuid
import json

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
app.debug = True

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Přesměrování na login stránku, pokud uživatel není přihlášen


@login_manager.user_loader
def load_user(username):
    user_data = get_user(username)
    if user_data:
        return User(user_data["username"], user_data["password_hash"], user_data["email"])
    return None
from app import routes
from werkzeug.security import generate_password_hash

# Funkce pro registraci uživatele do Neo4j
def register_user(username, email, password):
    with neo4j_driver.session() as session:
        # Zkontroluj, zda uživatel nebo email existuje
        result = session.run(
            "MATCH (u:User) WHERE u.username = $username OR u.email = $email RETURN u",
            username=username,
            email=email
        )
        if result.single():
            return "Uživatel již existuje"

        # Vlož uživatele
        password_hash = generate_password_hash(password)
        session.run(
            "CREATE (u:User {username: $username, email: $email, password_hash: $password_hash})",
            username=username,
            email=email,
            password_hash=password_hash
        )
        return "Uživatel úspěšně zaregistrován"


from werkzeug.security import check_password_hash

# Funkce pro přihlášení uživatele
def login_user(username, password):
    user = get_user(username)
    if not user:
        return "Uživatel nenalezen"

    # Ověření hesla
    if check_password_hash(user["password_hash"], password):
        # Vytvoření unikátního session ID
        session_id = str(uuid.uuid4())
        session_data = {
            "username": username,
            "email": user["email"]
        }

        # Uložení session do Redis
        redis_client.setex(f"session:{session_id}", 3600, json.dumps(session_data))  # Expirování po 1 hodině
        return {"success": True, "message": "Přihlášení úspěšné", "session_id": session_id}
    else:
        return {"success": False, "message": "Špatné heslo"}