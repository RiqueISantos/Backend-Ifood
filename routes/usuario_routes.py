import os
import traceback
from flask import Blueprint, request, jsonify
from database import SessionLocal
from dotenv import load_dotenv
from controllers.usuario_controller import UsuarioController
from auth_sms import AuthSmsService
from twilio.base.exceptions import TwilioRestException
from auth import criar_token_jwt, token_obrigatorio
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests



load_dotenv()

# Pega o Client ID do Google direto do .env
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

usuario_bp = Blueprint("usuarios", __name__, url_prefix="/usuarios")

sms_service = AuthSmsService()


@usuario_bp.route("/sms/enviar/<string:email>", methods=["POST"])
def enviar_sms(email):
    """Reenvia o código SMS. O email vem na URL para identificar o usuário."""
    db = SessionLocal()
    try:
        controller = UsuarioController(db, sms_service=sms_service)
        controller.reenviar_codigo(email)
        return jsonify({"mensagem": "Código reenviado com sucesso."}), 200
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    except TwilioRestException:
        return jsonify({"erro": "Não foi possível enviar o código. Verifique o número cadastrado."}), 400
    except Exception:
        return jsonify({"erro": "Erro interno no servidor."}), 500
    finally:
        db.close()


@usuario_bp.route("/sms/ativar/<string:email>", methods=["POST"])
def ativar_conta_sms(email):
    """Ativa a conta. O email vem na URL, só o código no body."""
    dados = request.get_json()
    codigo = dados.get("codigo") if dados else None

    if not codigo:
        return jsonify({"erro": "Código é obrigatório."}), 400

    db = SessionLocal()
    try:
        controller = UsuarioController(db, sms_service=sms_service)
        controller.ativar_conta(email, codigo)
        return jsonify({"mensagem": "Conta ativada com sucesso! Faça login para continuar."}), 200
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    except Exception:
        return jsonify({"erro": "Erro interno no servidor."}), 500
    finally:
        db.close()


@usuario_bp.route("/cadastro", methods=["POST"])
def cadastrar():
    dados = request.get_json()
    db = SessionLocal()
    try:
        controller = UsuarioController(db, sms_service=sms_service)
        controller.cadastrar(dados)
        return jsonify({
            "mensagem": "Cadastro realizado! Um código de verificação foi enviado para o seu WhatsApp."
        }), 201
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    except TwilioRestException:
        return jsonify({"erro": "Cadastro criado, mas não foi possível enviar o SMS."}), 201
    except Exception:
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

    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    except Exception:
        traceback.print_exc()
        return jsonify({"erro": "Erro interno no servidor."}), 500
    finally:
        db.close()


@usuario_bp.route("/login/google", methods=["POST"])
def login_google():
    dados = request.get_json()
    token_google = dados.get("token_google")

    if not token_google:
        return jsonify({"erro": "Token do Google não fornecido."}), 400

    # Verifica se a variável de ambiente foi carregada corretamente
    if not GOOGLE_CLIENT_ID:
        return jsonify({"erro": "Configuração do servidor ausente (GOOGLE_CLIENT_ID)."}), 500

    db = SessionLocal()
    try:
        # Valida o token com o Google
        idinfo = id_token.verify_oauth2_token(
            token_google, 
            google_requests.Request(), 
            GOOGLE_CLIENT_ID
        )

        email = idinfo.get('email')
        nome = idinfo.get('name', 'Usuário Google')

        controller = UsuarioController(db)
        usuario = controller.autenticar_ou_criar_google(email, nome)

        # Cria o SEU token JWT
        token_de_acesso = criar_token_jwt(usuario.id)

        return jsonify({
            "mensagem": "Login com Google realizado com sucesso!",
            "access_token": token_de_acesso,
            "token_type": "bearer",
            "usuario": {"id": usuario.id, "nome": usuario.nome, "email": usuario.email}
        }), 200
    except ValueError as e:
        print(f"ERRO DO GOOGLE DETALHADO: {str(e)}")
        return jsonify({"erro": f"Token do Google inválido: {str(e)}"}), 401
    except Exception:
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
    except Exception:
        return jsonify({"erro": "Erro interno no servidor."}), 500
    finally:
        db.close()


@usuario_bp.route("/deletar", methods=["DELETE"])
@token_obrigatorio
def deletar_conta(usuario_id):
    db = SessionLocal()
    try:
        controller = UsuarioController(db)
        controller.deletar(usuario_id)
        return jsonify({"mensagem": "Conta deletada com sucesso!"}), 200
    except ValueError as e:
        return jsonify({"erro": str(e)}), 404
    except Exception:
        return jsonify({"erro": "Erro interno no servidor."}), 500
    finally:
        db.close()


@usuario_bp.route("/alterar", methods=["PUT"])
@token_obrigatorio
def alterar(usuario_id):
    dados = request.get_json()
    db = SessionLocal()

    try:
        controller = UsuarioController(db)
        usuario_atualizado = controller.atualizar(usuario_id, dados)
        return jsonify({
            "mensagem": "Conta atualizada com sucesso!",
            "usuario": usuario_atualizado.to_dict()
        }), 200
    except ValueError as e:
        return jsonify({"erro": str(e)}), 404
    except Exception:
        return jsonify({"erro": "Erro interno no servidor."}), 500
    finally:
        db.close()