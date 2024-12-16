from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, username, password_hash, email, gender=None, birthdate=None, zodiac=None,relationship_status=None, bio=None, profile_photo=None):
        self.username = username
        self.password_hash = password_hash
        self.email = email

        #úprava profilu
        self.gender = gender
        self.birthdate = birthdate
        self.zodiac = zodiac
        self.relationship_status = relationship_status
        self.bio = bio
        self.profile_photo = profile_photo

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