import os
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

from database import engine, Base
import models
from routes.usuario_routes import usuario_bp

app = Flask(__name__)

# O Flask ainda precisa de uma secret key geral por segurança
app.secret_key = os.getenv("SECRET_KEY_FLASK") or "fallback_secreto_desenvolvimento"
app.config["SECRET_KEY"] = app.secret_key

CORS(app, resources={
    r"/*": {
        "origins": [
            "http://localhost:5173", 
            "http://127.0.0.1:5173", 
            "http://localhost:5174", 
            "http://127.0.0.1:5174"
        ]
    }
})

Base.metadata.create_all(bind=engine)

# Registra as rotas
app.register_blueprint(usuario_bp)

@app.route("/")
def index():
    return jsonify({"mensagem": "API do iFood rodando com sucesso!"})

if __name__ == "__main__":
    app.run(debug=True, port=5000)