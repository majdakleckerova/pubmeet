from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required
from models.user import User
from werkzeug.security import check_password_hash
from webik import db

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Najdi uživatele podle jména
        user = User.query.filter_by(username=username).first()

        # Ověření hesla pomocí metody check_password
        if not user or not user.check_password(password):
            flash('Nesprávné uživatelské jméno nebo heslo')
            return redirect(url_for('auth.login'))

        # Přihlášení uživatele
        login_user(user)
        return redirect(url_for('main.profile'))  # Přesměrování po přihlášení

    return render_template('prihlaseni.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
