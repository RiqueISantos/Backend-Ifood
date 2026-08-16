from flask import Blueprint, request, jsonify
from database import SessionLocal
from controllers.usuario_controller import UsuarioController
from auth import criar_token_jwt, token_obrigatorio

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

        token_de_acesso = criar_token_jwt(usuario.id)
        return jsonify({
            "mensagem": "Login realizado com sucesso!",
            "access_token": token_de_acesso,
            "token_type": "bearer"
        }), 200
        
# ... resto do código de login ...
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    except Exception as e:
        # AS DUAS LINHAS ABAIXO SÃO A MÁGICA:
        import traceback
        traceback.print_exc() 
        
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




@usuario_bp.route("/deletar", methods=["DELETE"]) # <--- URL simples! Sem email aqui.
@token_obrigatorio
def deletar_conta(usuario_id): # <--- O decorador injeta o usuario_id aqui automaticamente
    db = SessionLocal()
    try:
        controller = UsuarioController(db)
        
        # Manda deletar direto, pois o ID veio confiavelmente do Token
        controller.deletar(usuario_id) 
        
        return jsonify({"mensagem": "Conta deletada com sucesso!"}), 200
        
    except ValueError as e:
        return jsonify({"erro": str(e)}), 404
    except Exception as e:
        return jsonify({"erro": "Erro interno no servidor."}), 500
    finally:
        db.close()



@usuario_bp.route("/alterar", methods=["PUT"])
@token_obrigatorio
def alterar(usuario_id): # <--- O decorador injeta o ID aqui novamente!
    # Pega os novos dados (nome, telefone, etc) que vieram no corpo da requisição (Body)
    dados = request.get_json() 
    db = SessionLocal()
    
    try:
        controller = UsuarioController(db)
        
        # Manda o Controller atualizar o usuário dono daquele ID
        usuario_atualizado = controller.atualizar(usuario_id, dados)
        
        return jsonify({
            "mensagem": "Conta atualizada com sucesso!",
            "usuario": usuario_atualizado.to_dict() 
        }), 200
        
    except ValueError as e:
        return jsonify({"erro": str(e)}), 404
    except Exception as e:
        return jsonify({"erro": "Erro interno no servidor."}), 500
    finally:
        db.close()