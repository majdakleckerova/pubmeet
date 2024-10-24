from flask import render_template, request, redirect, url_for, flash
from flask_login import login_user, login_required, logout_user
from werkzeug.security import check_password_hash
from app import app
from app.models.user import User
from werkzeug.security import generate_password_hash
from app import db
@app.route('/prihlaseni', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Najdi uživatele podle uživatelského jména
        user = User.find_by_username(username)
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('profile'))  # Přesměrování na profil po úspěšném přihlášení
        else:
            flash('Špatné uživatelské jméno nebo heslo')
    
    return render_template('prihlaseni.html')

@app.route('/profil')
@login_required  # Zabezpečí, že jen přihlášení uživatelé mají přístup
def profile():
    return render_template('profil.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))
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

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        password_hash = generate_password_hash(password)
        
        # Zkontroluj, zda už uživatel neexistuje
        if User.find_by_username(username):
            flash('Uživatel s tímto jménem již existuje')
        else:
            # Vlož nového uživatele do MongoDB
            db.users.insert_one({
                "username": username,
                "password_hash": password_hash
            })
            flash('Registrace úspěšná, nyní se můžete přihlásit')
            return redirect(url_for('login'))
    
    return render_template('register.html')