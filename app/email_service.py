import secrets
from flask_mail import Mail, Message
from flask import current_app

mail = Mail()  

def send_verification_email(email, token):
    verification_link = f"http://127.0.0.1:5001/verify_email?token={token}"
    msg = Message("pubMeet: Dokončení registrace", recipients=[email])
    msg.body = f"Pro ověření vaší e-mailové adresy klikněte na následující odkaz: {verification_link}"
    mail.send(msg)

def send_new_password_email(email, new_password):
    msg = Message("Obnovení hesla", recipients=[email])
    msg.body = f"Vaše nové heslo je: {new_password}\n\nPo přihlášení si jej nezapomeňte změnit."
    mail.send(msg)
