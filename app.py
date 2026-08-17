from flask import Flask, jsonify
from flask_cors import CORS
from database import engine, Base
import models
from routes.usuario_routes import usuario_bp

Base.metadata.create_all(bind=engine)

app = Flask(__name__)

# Permite requisições do frontend Vite em desenvolvimento
CORS(app, resources={r"/*": {"origins": ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"]}})

app.register_blueprint(usuario_bp)

@app.route("/")
def index():
    return jsonify({"mensagem": "API do iFood rodando com sucesso!"})

if __name__ == "__main__":
    app.run(debug=True, port=5000)