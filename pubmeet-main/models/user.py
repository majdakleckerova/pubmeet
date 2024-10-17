from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# Inicializace databázového objektu
db = SQLAlchemy()

# Definice modelu User
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)  # Primární klíč
    username = db.Column(db.String(150), unique=True, nullable=False)  # Uživatelské jméno
    password_hash = db.Column(db.String(200), nullable=False)  # Hash hesla

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
