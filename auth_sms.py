import os
import re
import secrets
import time
from dotenv import load_dotenv
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from models.models import SmsVerificacao

load_dotenv()

CODIGO_TTL_SEGUNDOS      = 300   # 5 min para digitar o código
VERIFICACAO_TTL_SEGUNDOS = 900   # 15 min de janela após verificar


class AuthSmsService:

    def __init__(self):
        self.account_sid   = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token    = os.getenv("TWILIO_AUTH_TOKEN")
        self.template_sid  = os.getenv("TWILIO_TEMPLATE_SID")
        self.whatsapp_from = os.getenv("TWILIO_WHATSAPP_FROM")

        if not all([self.account_sid, self.auth_token, self.template_sid, self.whatsapp_from]):
            raise ValueError("Credenciais Twilio não configuradas")

        self.client = Client(self.account_sid, self.auth_token)

    # ── Helpers ───────────────────────────────────────────────────────────

    def limpar_numero(self, celular: str) -> str:
        apenas_numeros = re.sub(r"\D", "", celular)
        if not apenas_numeros.startswith("55"):
            apenas_numeros = "55" + apenas_numeros
        return f"+{apenas_numeros}"

    # ── Envio ─────────────────────────────────────────────────────────────

    def enviar_verificacao(self, celular: str, db) -> str:
        """Envia código via WhatsApp e persiste no banco."""
        numero = self.limpar_numero(celular)
        codigo = f"{secrets.randbelow(1_000_000):06d}"

        try:
            message = self.client.messages.create(
                from_=f"whatsapp:{self.whatsapp_from}",
                to=f"whatsapp:{numero}",
                content_sid=self.template_sid,
                content_variables=f'{{"1": "{codigo}"}}'
            )

            # Remove registros antigos deste número antes de criar novo
            db.query(SmsVerificacao).filter(
                SmsVerificacao.numero == numero,
                SmsVerificacao.verificado == False  # noqa: E712
            ).delete(synchronize_session=False)

            registro = SmsVerificacao(
                numero=numero,
                codigo=codigo,
                expira_em=time.time() + CODIGO_TTL_SEGUNDOS,
                verificado=False,
                verificado_expira_em=None,
            )
            db.add(registro)
            db.commit()

            print(f"Código enviado para {numero}")
            return message.sid

        except TwilioRestException as e:
            print(f"Erro Twilio: {e.msg}")
            raise

    # ── Verificação ───────────────────────────────────────────────────────

    def verificar_codigo(self, celular: str, codigo: str, db) -> bool:
        """Valida o código no banco. Marca como verificado se correto."""
        numero = self.limpar_numero(celular)

        registro = (
            db.query(SmsVerificacao)
            .filter(
                SmsVerificacao.numero == numero,
                SmsVerificacao.verificado == False  # noqa: E712
            )
            .order_by(SmsVerificacao.expira_em.desc())
            .first()
        )

        if not registro:
            print("Nenhum código pendente para este número")
            return False

        if time.time() > registro.expira_em:
            print("Código expirado")
            db.delete(registro)
            db.commit()
            return False

        if not secrets.compare_digest(registro.codigo, str(codigo)):
            print("Código incorreto")
            return False

        print("Código válido")
        registro.verificado = True
        registro.verificado_expira_em = time.time() + VERIFICACAO_TTL_SEGUNDOS
        db.commit()
        return True

    # ── Checagem de verificação prévia ────────────────────────────────────

    def telefone_esta_verificado(self, celular: str, db) -> bool:
        """Retorna True se o número passou pela verificação recentemente."""
        numero = self.limpar_numero(celular)

        registro = (
            db.query(SmsVerificacao)
            .filter(
                SmsVerificacao.numero == numero,
                SmsVerificacao.verificado == True  # noqa: E712
            )
            .order_by(SmsVerificacao.verificado_expira_em.desc())
            .first()
        )

        if not registro or not registro.verificado_expira_em:
            return False

        if time.time() > registro.verificado_expira_em:
            db.delete(registro)
            db.commit()
            return False

        return True

    def invalidar_verificacao(self, celular: str, db) -> None:
        """Remove a marcação de verificado após o cadastro ser concluído."""
        numero = self.limpar_numero(celular)
        db.query(SmsVerificacao).filter(
            SmsVerificacao.numero == numero
        ).delete(synchronize_session=False)
        db.commit()
