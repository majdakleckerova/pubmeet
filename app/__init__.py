from flask import Flask
from flask_login import LoginManager
from app.map import map_bp
from app.routes import auth_bp
from app.extensions import socketio
from app.db.neo4j import get_neo4j_session
from app.models.user import User
import os
from flask_session import Session

def create_app():
    app = Flask(__name__)
    
    # Nastavení tajného klíče
    app.secret_key = os.getenv('SECRET_KEY', 'default_secret_key')

    # Konfigurace session
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_PERMANENT'] = False
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')

    Session(app)  # Inicializace Flask-Session

    # Registrace blueprintů
    app.register_blueprint(map_bp)
    app.register_blueprint(auth_bp)

    # Inicializace Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'  # Výchozí stránka přihlášení
    login_manager.login_message = "Pro přístup se musíte přihlásit."
    login_manager.login_message_category = "info"

    @login_manager.user_loader
    def load_user(username):
        with get_neo4j_session() as session:
            result = session.run("MATCH (u:User {username: $username}) RETURN u", username=username)
            user_data = result.single()
            if user_data:
                user = user_data['u']
                return User(username=user['username'],
                            password_hash=user['password'],
                            email=user['email'],
                            gender=user["gender"],
                            birthdate=user["birthdate"],
                            zodiac=user["zodiac"],
                            relationship_status=user["relationship_status"],
                            bio=user["bio"],
                            profile_photo=user['profile_photo']
                            )
            return None

    # Inicializace Socket.IO
    socketio.init_app(app)

    return app