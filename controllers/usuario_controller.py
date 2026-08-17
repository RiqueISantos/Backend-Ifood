from werkzeug.security import generate_password_hash, check_password_hash
from models.models import Usuario

class UsuarioController:
    def __init__(self, db, sms_service=None):
        self.db = db
        self.sms_service = sms_service

    def gerar_hash(self, senha: str):
        return generate_password_hash(senha)

    def autenticar(self, email, senha):
        if not email or not senha:
            raise ValueError("Email e senha são obrigatórios.")

        usuario = self.db.query(Usuario).filter(Usuario.email == email).first()

        if not usuario or not usuario.senha_hash or not check_password_hash(usuario.senha_hash, senha):
            return None

        if not usuario.status:
            raise ValueError("Conta não ativada. Verifique o código enviado por SMS.")

        return usuario

    def cadastrar(self, dados):
        if not dados.get("nome") or not dados.get("email") or not dados.get("senha") or not dados.get("telefone"):
            raise ValueError('Dados obrigatórios não preenchidos.')

        telefone = dados["telefone"]

        if self.db.query(Usuario).filter(Usuario.email == dados["email"]).first():
            raise ValueError("Email já cadastrado.")


        novo_usuario = Usuario(
            nome=dados["nome"],
            email=dados["email"],
            senha_hash=self.gerar_hash(dados["senha"]),
            telefone=telefone,
            provedor_auth=dados.get("provedor_auth", "local"),
            status=False
        )

        self.db.add(novo_usuario)
        self.db.commit()
        self.db.refresh(novo_usuario)


        if self.sms_service:
            self.sms_service.enviar_verificacao(telefone)

        return novo_usuario

    def ativar_conta(self, email: str, codigo: str):
        """Busca o usuário pelo email, valida o código SMS e ativa a conta."""
        if not self.sms_service:
            raise ValueError("Serviço de SMS não disponível.")

        usuario = self.db.query(Usuario).filter(Usuario.email == email).first()
        if not usuario:
            raise ValueError("Usuário não encontrado.")

        if usuario.status:
            raise ValueError("Conta já está ativa.")

        if not usuario.telefone:
            raise ValueError("Usuário não possui telefone cadastrado.")

        valido = self.sms_service.verificar_codigo(usuario.telefone, codigo)
        if not valido:
            raise ValueError("Código inválido ou expirado.")

        usuario.status = True
        self.db.commit()
        self.db.refresh(usuario)
        return usuario

    def reenviar_codigo(self, email: str):
        """Busca o telefone pelo email e reenvia o código SMS."""
        if not self.sms_service:
            raise ValueError("Serviço de SMS não disponível.")

        usuario = self.db.query(Usuario).filter(Usuario.email == email).first()
        if not usuario:
            raise ValueError("Usuário não encontrado.")

        if usuario.status:
            raise ValueError("Conta já está ativa.")

        if not usuario.telefone:
            raise ValueError("Usuário não possui telefone cadastrado.")

        self.sms_service.enviar_verificacao(usuario.telefone)
        return True

    def autenticar_google(self, dados_google):
        email = dados_google.get("email")
        nome = dados_google.get("name")

        if not email:
            raise ValueError("Email não retornado pelo Google.")

        usuario = self.db.query(Usuario).filter(Usuario.email == email).first()

        if usuario:
            if usuario.provedor_auth == "local":
                usuario.provedor_auth = "google_local"
                self.db.commit()
                self.db.refresh(usuario)
            return usuario

        novo_usuario = Usuario(
            nome=nome,
            email=email,
            senha_hash=None,
            telefone=None,
            provedor_auth="google"
        )
        self.db.add(novo_usuario)
        self.db.commit()
        self.db.refresh(novo_usuario)
        return novo_usuario

    def buscar_usuario(self, usuario_email):
        usuario = self.db.query(Usuario).filter(Usuario.email == usuario_email).first()
        if not usuario:
            raise ValueError("Usuário não encontrado.")
        return usuario

    def deletar(self, usuario_id: int):
        usuario = self.db.query(Usuario).filter(Usuario.id == usuario_id).first()

        if not usuario:
            raise ValueError("Usuário não encontrado.")

        self.db.delete(usuario)
        self.db.commit()
        return True

    def atualizar(self, usuario_id: int, dados):
        usuario = self.db.query(Usuario).filter(Usuario.id == usuario_id).first()
        if not usuario:
            raise ValueError("Usuário não encontrado.")

        if "nome" in dados:
            usuario.nome = dados['nome']

        if "telefone" in dados:
            usuario.telefone = dados['telefone']

        if "senha" in dados:
            usuario.senha_hash = self.gerar_hash(dados['senha'])

        self.db.commit()
        self.db.refresh(usuario)
        return usuario