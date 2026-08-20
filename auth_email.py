"""
auth_email.py

Serviço de verificação de e-mail via código de 6 dígitos.
Usa a biblioteca requests para chamar a API do SendGrid.
Os códigos são persistidos no PostgreSQL para sobreviver a restarts do container.

Variáveis necessárias no .env:
    SENDGRID_API_KEY          - chave da API do SendGrid
    SENDGRID_FROM_EMAIL       - e-mail remetente verificado no SendGrid
    EMAIL_VERIFICATION_EXPIRY - TTL do código em segundos (padrão: 300)
"""

import os
import re
import secrets
import time
import requests
from dotenv import load_dotenv
from models.models import EmailVerificacao

load_dotenv()

CODIGO_TTL_SEGUNDOS = int(os.getenv("EMAIL_VERIFICATION_EXPIRY", "300"))


class AuthEmailService:

    def __init__(self):
        self.api_key    = os.getenv("SENDGRID_API_KEY",    "")
        self.from_email = os.getenv("SENDGRID_FROM_EMAIL", "")
        self.from_name  = "iFood Clone"

    # ── Público ───────────────────────────────────────────────────────────

    def enviar_verificacao(self, email: str, db) -> str:
        """Gera um código de 6 dígitos, persiste no banco e envia por e-mail."""
        email = email.strip().lower()
        if not self._email_valido(email):
            raise ValueError("E-mail inválido.")

        codigo = f"{secrets.randbelow(1_000_000):06d}"

        # Remove códigos antigos deste e-mail antes de inserir novo
        db.query(EmailVerificacao).filter(
            EmailVerificacao.email == email
        ).delete(synchronize_session=False)

        registro = EmailVerificacao(
            email=email,
            codigo=codigo,
            expira_em=time.time() + CODIGO_TTL_SEGUNDOS,
        )
        db.add(registro)
        db.commit()

        if self.api_key and self.from_email:
            self._enviar_sendgrid(email, codigo)
        else:
            print(f"[DEV] Código de e-mail para {email}: {codigo}")

        return codigo

    def verificar_codigo(self, email: str, codigo: str, db) -> bool:
        """Retorna True se o código for válido e não expirado, e remove do banco."""
        email = email.strip().lower()

        registro = (
            db.query(EmailVerificacao)
            .filter(EmailVerificacao.email == email)
            .order_by(EmailVerificacao.expira_em.desc())
            .first()
        )

        if not registro:
            return False

        if time.time() > registro.expira_em:
            db.delete(registro)
            db.commit()
            return False

        valido = secrets.compare_digest(registro.codigo, str(codigo).strip())
        if valido:
            db.delete(registro)
            db.commit()
        return valido

    # ── Privado ───────────────────────────────────────────────────────────

    def _enviar_sendgrid(self, destino: str, codigo: str):
        """Envia o e-mail usando a API REST do SendGrid via requests."""
        html = f"""
        <div style="font-family:Inter,sans-serif;max-width:480px;margin:auto;padding:32px;
                    background:#fff;border-radius:12px;box-shadow:0 4px 16px rgba(0,0,0,.08)">
          <div style="text-align:center;margin-bottom:24px">
            <span style="font-size:28px;font-weight:800;color:#EA1D2C">iFood</span>
          </div>
          <h2 style="color:#212121;font-size:20px;margin-bottom:8px">Verifique seu e-mail</h2>
          <p style="color:#616161;margin-bottom:24px">Use o código abaixo para confirmar seu cadastro.</p>
          <div style="text-align:center;background:#f9f9f9;border-radius:8px;padding:20px;margin-bottom:24px">
            <span style="font-size:36px;font-weight:700;letter-spacing:8px;color:#EA1D2C">{codigo}</span>
          </div>
          <p style="color:#9e9e9e;font-size:13px">
            Este código expira em {CODIGO_TTL_SEGUNDOS // 60} minutos.
            Se você não solicitou este código, ignore este e-mail.
          </p>
        </div>
        """

        payload = {
            "personalizations": [{"to": [{"email": destino}]}],
            "from": {"email": self.from_email, "name": self.from_name},
            "subject": "Seu código de verificação iFood",
            "content": [
                {
                    "type":  "text/plain",
                    "value": f"Seu código de verificação é: {codigo}\n\nExpira em {CODIGO_TTL_SEGUNDOS // 60} minutos.",
                },
                {"type": "text/html", "value": html},
            ],
        }

        resp = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            json=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type":  "application/json",
            },
            timeout=10,
        )

        if resp.status_code not in (200, 202):
            raise ValueError(f"SendGrid erro {resp.status_code}: {resp.text}")

        print(f"[SendGrid] E-mail enviado para {destino} — status {resp.status_code}")

    @staticmethod
    def _email_valido(email: str) -> bool:
        return bool(re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email))
