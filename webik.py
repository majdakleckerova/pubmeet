
from flask import Flask, render_template
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from models.user import User  # Import modelu uživatele

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tajneheslo'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'  # Napojení na databázi
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'  # Nastavuje stránku pro přihlášení, pokud není uživatel přihlášen

# Funkce pro načtení uživatele z databáze podle ID
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/")
@app.route("/home")
def domovska_stranka():
    return render_template("index.html")

@app.route("/profil")
def dejv_kralos():
    return render_template("profil.html")

@app.route("/mapik")
def mapik():
    return render_template("mapik.html")

@app.route("/chabri")
def chabri():
    return render_template("chabri.html")

@app.route("/nastaveni")
def nastaveni():
    return render_template("nastaveni.html")

@app.route("/prihlaseni")
def prihlaseni():
    return render_template("prihlaseni.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0",  port=4000, debug=True)
