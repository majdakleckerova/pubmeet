from flask import Blueprint, request, redirect, render_template, flash, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from app.db.neo4j import get_neo4j_session
from flask_login import login_required, login_user, logout_user, current_user
from app.models.user import User
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        if not username or not email or not password:
            flash("Vyplňte všechna pole.")
            return redirect(url_for('auth.register'))

        hashed_password = generate_password_hash(password)

        neo4j_session = get_neo4j_session()
        result = neo4j_session.run(
            "MATCH (u:User {username: $username}) RETURN u",
            username=username
        )
        if result.single():
            flash("Uživatelské jméno již existuje.")
            return redirect(url_for('auth.register'))

        neo4j_session.run(
            "CREATE (u:User {username: $username, email: $email, password: $password})",
            username=username, email=email, password=hashed_password
        )

        flash("Registrace proběhla úspěšně. Nyní se můžete přihlásit.")
        return redirect(url_for('auth.login'))

    return render_template('register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if not username or not password:
            flash("Vyplňte všechna pole.")
            return redirect(url_for('auth.login'))

        # Načti uživatele z Neo4j
        with get_neo4j_session() as session:
            result = session.run(
                "MATCH (u:User {username: $username}) RETURN u.password AS password",
                username=username
            )
            user = result.single()

            if not user:
                flash("Uživatelské jméno neexistuje.")
                return redirect(url_for('auth.login'))

            stored_password = user['password']
            if not check_password_hash(stored_password, password):
                flash("Špatné heslo.")
                return redirect(url_for('auth.login'))

        # Přihlásit uživatele pomocí Flask-Login
        login_user(User(username=username, password_hash=stored_password, email=""))
        flash(f"Vítejte, {username}!")
        return redirect(url_for('auth.profil'))

    return render_template('login.html')
@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Byli jste úspěšně odhlášeni.")
    return redirect(url_for('auth.login'))


@auth_bp.route('/profil')
@login_required
def profil():
    return render_template('profil.html')


@auth_bp.route("/")
@auth_bp.route("/home")
@login_required
def home():
    return render_template("home.html")


@auth_bp.route("/mapik")
@login_required
def mapik():
    return render_template("mapik.html")


@auth_bp.route("/chabri")
@login_required
def chabri():
    return render_template("chabri.html")