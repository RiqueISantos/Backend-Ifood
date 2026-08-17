import os
import re
import secrets
import time
from dotenv import load_dotenv
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

load_dotenv()

CODIGO_TTL_SEGUNDOS = 300     
VERIFICACAO_TTL_SEGUNDOS = 900 


class AuthSmsService:


    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.template_sid = os.getenv("TWILIO_TEMPLATE_SID")
        self.whatsapp_from = os.getenv("TWILIO_WHATSAPP_FROM")

        if not all([self.account_sid, self.auth_token, self.template_sid, self.whatsapp_from]):
            raise ValueError("Credenciais Twilio não configuradas")

        self.client = Client(self.account_sid, self.auth_token)

        self._codigos = {}
        self._verificados = {}

    def limpar_numero(self, celular: str) -> str:
        apenas_numeros = re.sub(r"\D", "", celular)

        if not apenas_numeros.startswith("55"):
            apenas_numeros = "55" + apenas_numeros

        return f"+{apenas_numeros}"

    def enviar_verificacao(self, celular: str) -> str:
        numero = self.limpar_numero(celular)
        codigo = f"{secrets.randbelow(1_000_000):06d}"

        try:
            message = self.client.messages.create(
                from_=f"whatsapp:{self.whatsapp_from}",
                to=f"whatsapp:{numero}",
                content_sid=self.template_sid,
                content_variables=f'{{"1": "{codigo}"}}'
            )

            self._codigos[numero] = {
                "codigo": codigo,
                "expira_em": time.time() + CODIGO_TTL_SEGUNDOS,
            }

            print(f"Código enviado para {numero}")
            return message.sid

        except TwilioRestException as e:
            print(f"Erro Twilio: {e.msg}")
            raise

    def verificar_codigo(self, celular: str, codigo: str) -> bool:
        numero = self.limpar_numero(celular)
        registro = self._codigos.get(numero)

        if not registro:
            print("Nenhum código enviado")
            return False

        if time.time() > registro["expira_em"]:
            print("Código expirado")
            del self._codigos[numero]
            return False

        if not secrets.compare_digest(registro["codigo"], str(codigo)):
            print("Código incorreto")
            return False

        print("Código válido")
        del self._codigos[numero]
        self._verificados[numero] = time.time() + VERIFICACAO_TTL_SEGUNDOS
        return True

    def telefone_esta_verificado(self, celular: str) -> bool:
        numero = self.limpar_numero(celular)
        expira_em = self._verificados.get(numero)

        if not expira_em:
            return False

        if time.time() > expira_em:
            del self._verificados[numero]
            return False

        return True

    def invalidar_verificacao(self, celular: str) -> None:
        numero = self.limpar_numero(celular)
        self._verificados.pop(numero, None)