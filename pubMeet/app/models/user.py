from flask_login import UserMixin
from bson.objectid import ObjectId



class User(UserMixin):
    def __init__(self, user_id, username, password_hash):
        self.id = user_id
        self.username = username
        self.password_hash = password_hash

    @staticmethod
    def get(user_id):
        from app import db
        user_data = db.users.find_one({"_id": user_id})
        if user_data:
            return User(str(user_data["_id"]), user_data["username"], user_data["password_hash"])
        return None

    @staticmethod
    def find_by_username(username):
        from app import db
        user_data = db.users.find_one({"username": username})
        if user_data:
            return User(str(user_data["_id"]), user_data["username"], user_data["password_hash"])
        return None
