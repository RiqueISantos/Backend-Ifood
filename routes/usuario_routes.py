import os
from flask import Blueprint, request, jsonify, url_for, redirect, session
from database import SessionLocal
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
from controllers.usuario_controller import UsuarioController
from auth_sms import AuthSmsService
from twilio.base.exceptions import TwilioRestException
from auth import criar_token_jwt, token_obrigatorio


load_dotenv()

SECRET_KEY_GOOGLE = os.getenv("SECRET_KEY_GOOGLE")
CLIENT_ID_GOOGLE = os.getenv("CLIENT_ID_GOOGLE")

usuario_bp = Blueprint("usuarios", __name__, url_prefix="/usuarios")

oauth = OAuth()

oauth.register(
    name="google",
    client_id=CLIENT_ID_GOOGLE,
    client_secret=SECRET_KEY_GOOGLE,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"}
)

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
            "mensagem": "Cadastro realizado! Um código de verificação foi enviado para o seu WhatsApp. "
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
        import traceback
        traceback.print_exc()
        return jsonify({"erro": "Erro interno no servidor."}), 500
    finally:
        db.close()


@usuario_bp.route("/login/google", methods=["GET"])
def login_google():
    redirect_uri = url_for("usuarios.google_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@usuario_bp.route("/google/callback", methods=["GET"])
def google_callback():
    db = SessionLocal()
    try:
        token = oauth.google.authorize_access_token()
        dados_google = token.get("userinfo")
        
        if not dados_google:
            return jsonify({"erro": "Falha ao obter informações do Google."}), 400

        controller = UsuarioController(db)
        usuario = controller.autenticar_google(dados_google)

        token_de_acesso = criar_token_jwt(usuario.id)

        return jsonify({
            "mensagem": "Login com Google realizado com sucesso!",
            "access_token": token_de_acesso,
            "token_type": "bearer",
            "usuario": usuario.to_dict()
        }), 200

    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    except Exception:
        import traceback
        traceback.print_exc()
        return jsonify({"erro": "Erro interno no servidor ao autenticar com o Google."}), 500
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