import secrets
from flask_mail import Mail, Message
from flask import current_app

mail = Mail()  

def send_verification_email(email, token):
    verification_link = f"http://127.0.0.1:5001/verify_email?token={token}"
    msg = Message("pubMeet: Dokončení registrace", recipients=[email])
    msg.body = f"Pro ověření vaší e-mailové adresy klikněte na následující odkaz: {verification_link}"
    mail.send(msg)
