from flask_socketio import SocketIO

socketio = SocketIO(cors_allowed_origins="*")  # Povolení CORS, pokud je potřeba