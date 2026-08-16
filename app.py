from flask import Flask, jsonify
from database import engine, Base
import models
from routes.usuario_routes import usuario_bp

Base.metadata.create_all(bind=engine)

app = Flask(__name__)

app.register_blueprint(usuario_bp)

@app.route("/")
def index():
    return jsonify({"mensagem": "API do iFood rodando com sucesso!"})

if __name__ == "__main__":
    app.run(debug=True, port=5000)