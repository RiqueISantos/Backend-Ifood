import os
import traceback
from flask import Blueprint, request, jsonify
from database import SessionLocal
from dotenv import load_dotenv
from controllers.usuario_controller import UsuarioController
from auth_sms import AuthSmsService
from auth_email import AuthEmailService
from models.models import Usuario
from twilio.base.exceptions import TwilioRestException
from auth import criar_token_jwt, token_obrigatorio
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

usuario_bp = Blueprint("usuarios", __name__, url_prefix="/usuarios")

sms_service   = AuthSmsService()
email_service = AuthEmailService()


# ── SMS avulso (verificação de celular ANTES do cadastro) ─────────────────────

@usuario_bp.route("/sms/enviar-numero", methods=["POST"])
def enviar_sms_numero():
    """Envia código SMS para um número de celular antes do cadastro."""
    dados    = request.get_json() or {}
    telefone = dados.get("telefone", "").strip()

    if not telefone:
        return jsonify({"erro": "Telefone é obrigatório."}), 400

    db = SessionLocal()
    try:
        controller = UsuarioController(db, sms_service=sms_service)
        controller.enviar_sms_para_numero(telefone)
        return jsonify({"mensagem": "Código enviado pelo WhatsApp."}), 200
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    except TwilioRestException:
        return jsonify({"erro": "Não foi possível enviar o código. Verifique o número."}), 400
    except Exception:
        traceback.print_exc()
        return jsonify({"erro": "Erro interno no servidor."}), 500
    finally:
        db.close()


@usuario_bp.route("/sms/verificar-numero", methods=["POST"])
def verificar_sms_numero():
    """Valida o código SMS de um número avulso (antes do cadastro)."""
    dados    = request.get_json() or {}
    telefone = dados.get("telefone", "").strip()
    codigo   = dados.get("codigo",   "").strip()

    if not telefone or not codigo:
        return jsonify({"erro": "Telefone e código são obrigatórios."}), 400

    db = SessionLocal()
    try:
        controller = UsuarioController(db, sms_service=sms_service)
        controller.verificar_sms_para_numero(telefone, codigo)
        return jsonify({"mensagem": "Celular verificado com sucesso."}), 200
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    except Exception:
        traceback.print_exc()
        return jsonify({"erro": "Erro interno no servidor."}), 500
    finally:
        db.close()


# ── Cadastro + envio de código de e-mail ──────────────────────────────────────

@usuario_bp.route("/cadastro", methods=["POST"])
def cadastrar():
    dados = request.get_json()
    db    = SessionLocal()
    try:
        controller = UsuarioController(db, sms_service=sms_service, email_service=email_service)
        controller.cadastrar(dados)
        return jsonify({
            "mensagem": "Cadastro realizado! Um código de verificação foi enviado para o seu e-mail."
        }), 201
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    except Exception:
        traceback.print_exc()
        return jsonify({"erro": "Erro interno no servidor."}), 500
    finally:
        db.close()


# ── Verificação de e-mail ─────────────────────────────────────────────────────

@usuario_bp.route("/email/ativar/<string:email>", methods=["POST"])
def ativar_conta_email(email):
    """Ativa a conta com o código recebido por e-mail."""
    dados  = request.get_json() or {}
    codigo = dados.get("codigo", "").strip()

    if not codigo:
        return jsonify({"erro": "Código é obrigatório."}), 400

    db = SessionLocal()
    try:
        controller = UsuarioController(db, email_service=email_service)
        controller.ativar_conta_email(email, codigo)
        return jsonify({"mensagem": "E-mail verificado! Conta ativada com sucesso."}), 200
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    except Exception:
        traceback.print_exc()
        return jsonify({"erro": "Erro interno no servidor."}), 500
    finally:
        db.close()


@usuario_bp.route("/email/reenviar/<string:email>", methods=["POST"])
def reenviar_email(email):
    """Reenvia o código de verificação por e-mail."""
    db = SessionLocal()
    try:
        controller = UsuarioController(db, email_service=email_service)
        controller.reenviar_codigo_email(email)
        return jsonify({"mensagem": "Código reenviado por e-mail."}), 200
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    except Exception:
        traceback.print_exc()
        return jsonify({"erro": "Erro interno no servidor."}), 500
    finally:
        db.close()


# ── SMS por conta cadastrada (legado / reenvio) ───────────────────────────────

@usuario_bp.route("/sms/enviar/<string:email>", methods=["POST"])
def enviar_sms(email):
    """Reenvia o código SMS pela conta já cadastrada."""
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
    """Ativa a conta com código SMS (fluxo legado)."""
    dados  = request.get_json() or {}
    codigo = dados.get("codigo", "").strip()

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


# ── Login ─────────────────────────────────────────────────────────────────────

@usuario_bp.route("/login", methods=["POST"])
def login():
    dados = request.get_json()
    db    = SessionLocal()
    try:
        controller = UsuarioController(db)
        usuario = controller.autenticar(dados.get("email"), dados.get("senha"))

        if not usuario:
            return jsonify({"erro": "Email ou senha inválidos."}), 401

        token_de_acesso = criar_token_jwt(usuario.id)
        return jsonify({
            "mensagem":     "Login realizado com sucesso!",
            "access_token": token_de_acesso,
            "token_type":   "bearer",
            "usuario":      usuario.to_dict(),
        }), 200

    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    except Exception:
        traceback.print_exc()
        return jsonify({"erro": "Erro interno no servidor."}), 500
    finally:
        db.close()


# ── Login Google ──────────────────────────────────────────────────────────────

@usuario_bp.route("/login/google", methods=["POST"])
def login_google():
    dados        = request.get_json() or {}
    token_google = dados.get("token_google")

    if not token_google:
        return jsonify({"erro": "Token do Google não fornecido."}), 400

    if not GOOGLE_CLIENT_ID:
        return jsonify({"erro": "Configuração do servidor ausente (GOOGLE_CLIENT_ID)."}), 500

    db = SessionLocal()
    try:
        idinfo = id_token.verify_oauth2_token(
            token_google,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
        )

        email = idinfo.get("email")
        nome  = idinfo.get("name", "Usuário Google")

        controller      = UsuarioController(db)
        usuario         = controller.autenticar_ou_criar_google(email, nome)
        token_de_acesso = criar_token_jwt(usuario.id)

        return jsonify({
            "mensagem":     "Login com Google realizado com sucesso!",
            "access_token": token_de_acesso,
            "token_type":   "bearer",
            "usuario":      usuario.to_dict(),
        }), 200
    except ValueError as e:
        return jsonify({"erro": f"Token do Google inválido: {str(e)}"}), 401
    except Exception:
        traceback.print_exc()
        return jsonify({"erro": "Erro interno no servidor."}), 500
    finally:
        db.close()


# ── CRUD de usuário ───────────────────────────────────────────────────────────

@usuario_bp.route("/verificar-email/<string:email>", methods=["GET"])
def verificar_email_existe(email):
    """Verifica se um e-mail já está cadastrado. Usado no fluxo de auth."""
    db = SessionLocal()
    try:
        usuario = db.query(Usuario).filter(Usuario.email == email.strip().lower()).first()
        return jsonify({"existe": usuario is not None}), 200
    except Exception:
        return jsonify({"existe": False}), 200
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
    db    = SessionLocal()
    try:
        controller          = UsuarioController(db)
        usuario_atualizado  = controller.atualizar(usuario_id, dados)
        return jsonify({
            "mensagem": "Conta atualizada com sucesso!",
            "usuario":  usuario_atualizado.to_dict(),
        }), 200
    except ValueError as e:
        return jsonify({"erro": str(e)}), 404
    except Exception:
        return jsonify({"erro": "Erro interno no servidor."}), 500
    finally:
        db.close()
