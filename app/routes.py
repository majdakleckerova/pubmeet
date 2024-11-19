from flask import render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app.db.neo4j import add_user, get_user
from app.models.user import User
from app.db.neo4j import neo4j_driver, get_pubs, increment_people_count, toggle_user_membership, toggle_user_hospital, update_session, validate_session, get_user
from app import app
from app.extentions import socketio 
from app.db.redis import redis_client, cache_user_session, get_user_session, delete_user_session
import uuid
import json
@app.route('/toggle_hospital', methods=['POST'])
def toggle_hospital():
    data = request.json
    pub_name = data.get('name')
    user_id = session.get('user_id')  # Získání ID uživatele z session

    if not user_id:
        return jsonify({"success": False, "message": "Uživatel není přihlášen."}), 403

    query_check = """
    MATCH (u:User {username: $user_id})-[:VISITS]->(h:Hospital {name: $pub_name})
    RETURN h.name AS current_pub
    """

    query_join = """
    MATCH (u:User {username: $user_id}), (h:Hospital {name: $pub_name})
    MERGE (u)-[:VISITS]->(h)
    SET h.people_count = COALESCE(h.people_count, 0) + 1
    RETURN h.people_count AS new_count
    """

    query_leave = """
    MATCH (u:User {username: $user_id})-[r:VISITS]->(h:Hospital {name: $pub_name})
    DELETE r
    SET h.people_count = COALESCE(h.people_count, 1) - 1
    RETURN h.people_count AS new_count
    """

    with neo4j_driver.session() as session:
        current_pub = session.run(query_check, user_id=user_id, pub_name=pub_name).single()
        if current_pub:
            # Uživatel odpojuje
            result = session.run(query_leave, user_id=user_id, pub_name=pub_name).single()
            new_count = result['new_count']
            socketio.emit('update_pub_count', {'pub_name': pub_name, 'new_count': new_count})
            return jsonify({"success": True, "action": "left", "new_count": new_count})
        else:
            # Uživatel připojuje
            result = session.run(query_join, user_id=user_id, pub_name=pub_name).single()
            new_count = result['new_count']
            socketio.emit('update_pub_count', {'pub_name': pub_name, 'new_count': new_count})
            return jsonify({"success": True, "action": "joined", "new_count": new_count})
@app.route('/toggle_membership', methods=['POST'])
def toggle_membership():
    """
    Připojení nebo odpojení uživatele k hospodě.
    """
    data = request.get_json()
    pub_name = data.get('name')
    user_id = session.get('user_id')  # Předpoklad: ID uživatele je uloženo v session

    if not pub_name:
        return jsonify({'success': False, 'message': 'Název hospody chybí.'}), 400

    if not user_id:
        return jsonify({'success': False, 'message': 'Uživatel není přihlášen.'}), 403

    # Změna členství v hospodě
    success, action, new_count = toggle_user_membership(user_id, pub_name)

    if success:
        socketio.emit('update_pub_count', {'pub_name': pub_name, 'new_count': new_count})
        return jsonify({'success': True, 'action': action, 'new_count': new_count})
    return jsonify({'success': False, 'message': 'Chyba při aktualizaci.'}), 500

@app.route('/get_pubs', methods=['GET'])
def get_pubs_route():
    """
    Vrátí seznam všech hospod z databáze Neo4j.
    """
    try:
        pubs = get_pubs()
        # Filtrovat a zpracovat data
        filtered_pubs = []
        for pub in pubs:
            # Ověřit, že data jsou platná
            if pub.get('latitude') is not None and pub.get('longitude') is not None:
                # Zkontrolovat NaN a nahradit výchozí hodnoty
                pub['latitude'] = pub['latitude'] if not isinstance(pub['latitude'], float) or not pub['latitude'] != pub['latitude'] else 0.0
                pub['longitude'] = pub['longitude'] if not isinstance(pub['longitude'], float) or not pub['longitude'] != pub['longitude'] else 0.0
                pub['address'] = pub.get('address', 'Neznámá adresa')
                pub['people_count'] = pub.get('people_count', 0)
                filtered_pubs.append(pub)

        return jsonify(filtered_pubs)
    except Exception as e:
        app.logger.error("Chyba při načítání hospod: %s", str(e))
        return jsonify({"error": str(e)}), 500

@app.route('/increment_people', methods=['POST'])
def increment_people():
    data = request.get_json()
    pub_name = data.get('name')

    if not pub_name:
        return jsonify({'success': False, 'message': 'Název hospody chybí.'}), 400

    new_count = increment_people_count(pub_name)
    if new_count is not None:
        socketio.emit('update_pub_count', {'pub_name': pub_name, 'new_count': new_count})
        return jsonify({'success': True, 'new_count': new_count})
    else:
        return jsonify({'success': False, 'message': 'Hospoda nenalezena.'}), 404
# Registrace uživatele
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        if get_user(username):
            flash("Uživatelské jméno je již obsazené.")
            return render_template('register.html')
        add_user(username, email, generate_password_hash(password))
        flash("Registrace úspěšná.")
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user_data = get_user(username)
        if not user_data or not check_password_hash(user_data['password_hash'], password):
            flash("Neplatné přihlašovací údaje.")
            return render_template('login.html')

        # Vytvoření session ID a uložení do Redis
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id
        session_data = {
            "username": user_data["username"],
            "email": user_data["email"]
        }
        cache_user_session(session_id, session_data)

        flash("Přihlášení úspěšné.")
        return redirect(url_for('profile'))
    return render_template('login.html')

@app.before_request
def validate_session():
    """
    Validuje session před zpracováním požadavku.
    """
    session_id = session.get('session_id')
    if session_id:
        session_data = get_user_session(session_id)
        if session_data:
            request.user = session_data  # Přidáme uživatelská data do requestu
            return  # Session je platná, pokračujeme
    if request.endpoint not in ('login', 'register', 'static'):
        # Nepustíme uživatele na chráněné stránky
        return redirect(url_for('login', next=request.path))

@app.route('/profil')
def profile():
    if not hasattr(request, 'user'):
        return redirect(url_for('login'))
    return render_template('profil.html', user=request.user)
@app.route('/logout')
def logout():
    session_id = session.pop('session_id', None)
    if session_id:
        delete_user_session(session_id)
    flash("Byli jste úspěšně odhlášeni.")
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

