from flask import Blueprint, request, redirect, render_template, flash, url_for, session, current_app, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from app.db.neo4j import get_neo4j_session, get_users, get_friends, get_friendship_status
from flask_login import login_required, login_user, logout_user, current_user
from app.email_service import send_verification_email
from app.models.user import User
import os
import uuid
from neo4j import GraphDatabase
from dotenv import load_dotenv
import pandas as pd

load_dotenv()
neo4j_driver = GraphDatabase.driver(
    os.getenv('NEO4J_URI'),
    auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD'))
)
def get_neo4j_session():
    return neo4j_driver.session()

auth_bp = Blueprint('auth', __name__)

def allowed_file(filename):
    allowed_extensions = {"png", "jpg", "jpeg","HEIC"}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

@auth_bp.context_processor
def inject_active_route():
    return {'active_route': request.path}

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

        verification_token = str(uuid.uuid4())

        neo4j_session.run(
            "CREATE (u:User {username: $username, email: $email, password: $password, "
            "nickname: $nickname, birthdate: $birthdate, favourite_drink: $favourite_drink, "
            "bio: $bio, profile_photo: $profile_photo, verified: false, verification_token: $verification_token})",
            username=username,
            email=email,
            password=hashed_password,
            nickname=None,
            birthdate=None,
            favourite_drink=None,
            bio=None,
            profile_photo="default.png",
            verification_token=verification_token
        )

        send_verification_email(email, verification_token)
        flash("Registrace proběhla úspěšně. Nyní se můžete přihlásit.")
        return redirect(url_for('auth.login'))

    return render_template('register.html')


@auth_bp.route('/edit_profile', methods=["GET", "POST"])
@login_required
def edit_profile():
    if request.method == "POST":
        nickname = request.form.get('nickname')
        birthdate = request.form.get('birthdate')
        favourite_drink = request.form.get('favourite_drink')
        bio = request.form.get('bio')
        profile_photo = request.files.get("profile_photo")

        photo_filename = current_user.profile_photo  # Pokud uživatel nemění fotku, použije se současná
        if profile_photo and allowed_file(profile_photo.filename):
            file_extension = profile_photo.filename.rsplit('.', 1)[1].lower()
            unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
            try:
                profile_photo.save(filepath)
                photo_filename = unique_filename
            except Exception as e:
                flash("Nepodařilo se uložit profilovou fotku.")
                return redirect(url_for('auth.edit_profile'))

        with get_neo4j_session() as session:
            query = "MATCH (u:User {username: $username}) SET "
            params = {'username': current_user.username}

            if nickname:
                query += "u.nickname = $nickname, "
                params['nickname'] = nickname
            if birthdate:
                query += "u.birthdate = $birthdate, "
                params['birthdate'] = birthdate
            if favourite_drink:
                query += "u.favourite_drink = $favourite_drink, "
                params['favourite_drink'] = favourite_drink
            if bio:
                query += "u.bio = $bio, "
                params['bio'] = bio
            if profile_photo:
                query += "u.profile_photo = $profile_photo, "
                params['profile_photo'] = photo_filename

            query = query.rstrip(", ")
            session.run(query, params)

        flash("Profil byl úspěšně aktualizován!")
        return redirect(url_for('auth.profile'))

    return render_template('edit_profile.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if not username or not password:
            flash("Vyplňte všechna pole.")
            return redirect(url_for('auth.login'))

        with get_neo4j_session() as session:
            result = session.run(
                "MATCH (u:User {username: $username}) RETURN u.password AS password, u.email AS email",
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
            
        login_user(User(username=username, password_hash=stored_password, email=user['email']))
        flash(f"Vítejte, {username}!")
        return redirect(url_for('auth.profile'))

    return render_template('login.html')


@auth_bp.route("/uzivatele")
@login_required
def index():
    users = get_users()

    search_query = request.args.get("q", "").strip().lower()

    users_with_status = []
    for user in users:
        status = get_friendship_status(current_user.username, user['username'])
        user['friendship_status'] = status
        users_with_status.append(user)

    users_with_status = sorted(users_with_status, key=lambda x: x['username'].lower())

    if search_query:
        users_with_status = [user for user in users_with_status if search_query in user['username'].lower()]

    return render_template("uzivatele.html", users=users_with_status, search_query=search_query)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Byli jste úspěšně odhlášeni.")
    return redirect(url_for('auth.login'))


@auth_bp.route('/profil', methods=['GET'])
@login_required
def profile():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))

    with neo4j_driver.session() as session:
        # Načte žádosti o přátelství
        query = """
        MATCH (u:User)-[r:FRIEND_REQUEST {status: 'REQUESTED'}]->(v:User)
        WHERE v.username = $username
        RETURN u.username AS username
        """
        result = session.run(query, username=current_user.username)
        friend_requests = [record["username"] for record in result]

        # Načte přátele
        query_friends = """
        MATCH (u:User)-[:FRIEND]-(f:User)
        WHERE u.username = $username
        RETURN f.username AS username
        """
        result_friends = session.run(query_friends, username=current_user.username)
        friends = [record["username"] for record in result_friends]
        # načte lajky
        query_likes = """
        MATCH (u:User)-[:LIKES]->(p:Pub)
        WHERE u.username = $username
        RETURN p.name AS pub_name
        """
        result_likes = session.run(query_likes, username=current_user.username)
        liked_pubs = [record["pub_name"] for record in result_likes]
        # načte lokaci
        query_location = """
        MATCH (u:User)-[:VISITS]->(p:Pub)
        WHERE u.username = $username
        RETURN p.name AS pub_name
        """
        result_location = session.run(query_location, username = current_user.username)
        location = [record["pub_name"] for record in result_location]

    return render_template('profil.html', friend_requests=friend_requests, friends=friends, liked_pubs=liked_pubs, location=location)



@auth_bp.route("/")
@auth_bp.route("/home")
def home():
    return render_template("home.html")


@auth_bp.route("/mapik")
@login_required
def mapik():
    return render_template("mapik.html")


@auth_bp.route('/uzivatele/<username>', methods=['GET'])
@login_required
def user_profile(username):
    with neo4j_driver.session() as session:
        # Načti informace o uživatelském profilu
        query_user = """
        MATCH (u:User {username: $username})
        RETURN u.username AS username, u.profile_photo AS profile_photo, 
               u.bio AS bio, u.birthdate AS birthdate, 
               u.favourite_drink AS favourite_drink, u.nickname AS nickname
        """
        result_user = session.run(query_user, username=username).single()

        if not result_user:
            flash("Uživatel nenalezen.", "danger")
            return redirect(url_for('auth.index'))

        # Připrav data pro šablonu
        user_data = {
            "username": result_user["username"],
            "profile_photo": result_user.get("profile_photo"),
            "bio": result_user.get("bio"),
            "birthdate": result_user.get("birthdate"),
            "favourite_drink": result_user.get("favourite_drink"),
            "nickname": result_user.get("nickname")
        }

        # Přidej stav přátelství mezi current_user a uživatelem
        friendship_status = get_friendship_status(current_user.username, username)
        user_data["friendship_status"] = friendship_status

        # Načti přátele (ne žádosti o přátelství)
        query_friends = """
        MATCH (u:User)-[:FRIEND]-(f:User)
        WHERE u.username = $username
        RETURN f.username AS username
        """
        result_friends = session.run(query_friends, username=username)
        friends = [record["username"] for record in result_friends]

        query_likes = """
        MATCH (u:User)-[:LIKES]-(p:Pub)
        WHERE u.username = $username
        RETURN p.name AS pub_name
        """
        result_likes = session.run(query_likes, username=username)
        liked_pubs = [record["pub_name"] for record in result_likes]

        is_friend = current_user.username in friends
        query_location = """
        MATCH (u:User)-[:VISITS]->(p:Pub)
        WHERE u.username = $username
        RETURN p.name AS pub_name
        """
        result_location = session.run(query_location, username=username)
        location = [record["pub_name"] for record in result_location] if is_friend else ["Přístupné pouze pro přátele."]

    return render_template(
        'uzivatel_profil.html', 
        user=user_data, 
        friends=friends, 
        liked_pubs=liked_pubs, 
        location=location, 
        is_friend=is_friend
    )

@auth_bp.route('/verify_email')
def verify_email():
    token = request.args.get('token')

    with get_neo4j_session() as session:
        user = session.run("MATCH (u:User {verification_token: $token}) RETURN u", token=token).single()
        
        if user:
            session.run("MATCH (u:User {verification_token: $token}) SET u.verified = true REMOVE u.verification_token", token=token)
            flash("E-mail ověřen! Můžete se přihlásit.")
            return redirect(url_for('auth.login'))
        else:
            flash("Neplatný nebo expirovaný token.")
            return redirect(url_for('auth.register'))

