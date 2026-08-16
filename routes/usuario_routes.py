from flask import Blueprint, request, jsonify
from database import SessionLocal
from controllers.usuario_controller import UsuarioController

usuario_bp = Blueprint("usuarios", __name__,url_prefix="/usuarios")

@usuario_bp.route("/cadastro",methods=["POST"])
def cadastrar():
    dados = request.get_json()
    db = SessionLocal()
    try:
        controller = UsuarioController(db)
        usuario = controller.cadastrar(dados)
        return jsonify({"mensagem": "Usuário criado com sucesso!"}), 201
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    except Exception as e:
        return jsonify({"erro": "Erro interno no servidor."}), 500
    finally:
        db.close()


@usuario_bp.route("/login", methods=["POST"])
def login():
    dados = request.get_json()
    db = SessionLocal()
    try:
        controller = UsuarioController(db)
        usuario = controller.autenticar(dados.get("email"), dados.get("senha"))
        
        if not usuario:
            return jsonify({"erro": "Email ou senha inválidos."}), 401
        
        return jsonify({"mensagem": "Login realizado com sucesso!"}), 200
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    except Exception as e:
        return jsonify({"erro": "Erro interno no servidor."}), 500
    finally:
        db.close()

@usuario_bp.route("/consultar/<string:email>", methods=["GET"])
def buscar_usuario(email):
    db = SessionLocal()
    try:
        controller = UsuarioController(db)
        usuario = controller.buscar_usuario(email)
        return jsonify(usuario.to_dict()), 200
    except ValueError as e:
        return jsonify({"erro": str(e)}), 404
    except Exception as e:
        return jsonify({"erro": "Erro interno no servidor."}), 500
    finally:
        db.close()