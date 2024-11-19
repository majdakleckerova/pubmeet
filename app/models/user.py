from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, username, password_hash, email):
        self.username = username
        self.password_hash = password_hash
        self.email = email

    def get_id(self):
        return self.username

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False