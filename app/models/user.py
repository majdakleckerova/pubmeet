from flask_login import UserMixin

class User(UserMixin):
    def __init__(self,
                  username,
                  email, 
                  password_hash, 
                  nickname=None, 
                  birthdate=None, 
                  favourite_drink=None, 
                  bio=None, 
                  profile_photo=None,
                  verified = False,
                  verification_token = None):
        
        # Registrace
        self.username = username
        self.email = email
        self.password_hash = password_hash

        # Úprava profilu
        self.nickname = nickname
        self.birthdate = birthdate
        self.favourite_drink = favourite_drink
        self.bio = bio
        self.profile_photo = profile_photo

        # Ověření e-mailu
        self.verified = verified
        self.verification_token = verification_token

    def get_id(self):
        return self.username

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return self.verified

    @property
    def is_anonymous(self):
        return False
