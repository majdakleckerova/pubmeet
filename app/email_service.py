import secrets
from flask_mail import Mail, Message
from flask import current_app

mail = Mail()  

def send_verification_email(email, token):
    verification_link = f"http://127.0.0.1:5001/verify_email?token={token}"
    msg = Message("Potvrzení e-mailu", recipients=[email])
    msg.body = f"Klikněte zde pro ověření vašeho e-mailu: {verification_link}"
    mail.send(msg)
