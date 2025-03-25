from flask import Flask
from flask_login import LoginManager
from app.map import map_bp
from app.routes import auth_bp
from app.db.neo4j import neo4j_bp
from app.extensions import socketio
from app.db.neo4j import get_neo4j_session
from app.models.user import User
from app.scheduler import scheduler
import os
from flask_session import Session
from flask_mail import Mail
from app.email_service import mail

def create_app():
    app = Flask(__name__)
    
    # Nastavení tajného klíče
    app.secret_key = os.getenv('SECRET_KEY', 'default_secret_key')

    # Konfigurace session
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_PERMANENT'] = False
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')

    Session(app)  # Inicializace Flask-Session

    # Konfigurace Flask-Mail
    app.config.from_mapping(
        MAIL_SERVER=os.getenv("MAIL_SERVER"),
        MAIL_PORT=int(os.getenv("MAIL_PORT")),
        MAIL_USE_TLS=os.getenv("MAIL_USE_TLS") == "True",
        MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
        MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
        MAIL_DEFAULT_SENDER=os.getenv("MAIL_DEFAULT_SENDER"),
    )

    mail.init_app(app)

    # Registrace blueprintů
    app.register_blueprint(map_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(neo4j_bp)

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

                verified_bool = user.get('verified') in [True, "true"]
                verified = verified_bool

                return User(username=user['username'],
                            password_hash=user['password'],
                            email=user['email'],  # Zachováno
                            nickname=user.get('nickname'),
                            birthdate=user.get('birthdate'),
                            favourite_drink=user.get('favourite_drink'),
                            bio=user.get('bio'),
                            profile_photo=user.get('profile_photo'),
                            verified=verified_bool,
                            verification_token=user.get('verification_token')
                            )
            return None

    # Inicializace Socket.IO
    socketio.init_app(app)

    return app
