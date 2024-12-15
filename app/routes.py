from flask import Blueprint, request, redirect, render_template, flash, url_for, session, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from app.db.neo4j import get_neo4j_session
from flask_login import login_required, login_user, logout_user, current_user
from app.models.user import User
import os
import uuid

auth_bp = Blueprint('auth', __name__)

def allowed_file(filename):
    allowed_extensions = {"png", "jpg", "jpeg"}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        profile_photo = request.files.get("profile_photo")


        if not username or not email or not password:
            flash("Vyplňte všechna pole.")
            return redirect(url_for('auth.register'))

        hashed_password = generate_password_hash(password)

        photo_filename = "default.png"
        if profile_photo and allowed_file(profile_photo.filename):
            file_extension = profile_photo.filename.rsplit('.', 1)[1].lower()
            unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)       
            try:
                profile_photo.save(filepath)
                photo_filename = unique_filename 
            except Exception as e:
                flash("Nepodařilo se uložit profilovou fotku.")
                return redirect(url_for('auth.register'))


        neo4j_session = get_neo4j_session()
        result = neo4j_session.run(
            "MATCH (u:User {username: $username}) RETURN u",
            username=username
        )
        if result.single():
            flash("Uživatelské jméno již existuje.")
            return redirect(url_for('auth.register'))

        neo4j_session.run(
            "CREATE (u:User {username: $username, email: $email, password: $password, profile_photo: $profile_photo})",
            username=username, email=email, password=hashed_password, profile_photo=photo_filename
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