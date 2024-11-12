from flask import render_template, request, redirect, url_for, flash
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import app
from app.db.neo4j import add_user, get_user
from app.models.user import User
# Registrace uživatele
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        password_hash = generate_password_hash(password)
        
        add_user(username, email, password_hash)
        flash("Registrace úspěšná, nyní se můžete přihlásit")
        return redirect(url_for('login'))
    return render_template('register.html')

# Přihlášení uživatele

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user_data = get_user(username)
        if user_data and check_password_hash(user_data["password_hash"], password):
            user = User(user_data["username"], user_data["password_hash"], user_data["email"])
            login_user(user)
            flash("Přihlášení úspěšné")
            return redirect(url_for('profile'))
        else:
            flash("Špatné uživatelské jméno nebo heslo")
    
    return render_template('login.html')

@app.route('/profil')
def profile():
    return render_template('profil.html', user=current_user)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Byli jste odhlášeni")
    return redirect(url_for('login'))
@app.route("/")
@app.route("/home")
def home():
    return render_template("home.html")

@app.route("/mapik")
def mapik():
    return render_template("mapik.html")

@app.route("/chabri")
def chabri():
    return render_template("chabri.html")

