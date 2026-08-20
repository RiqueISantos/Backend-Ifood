from werkzeug.security import generate_password_hash, check_password_hash
from models.models import Usuario

class UsuarioController:
    def __init__(self, db, sms_service=None, email_service=None):
        self.db            = db
        self.sms_service   = sms_service
        self.email_service = email_service

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

        # Envia código de verificação por e-mail (novo fluxo iFood)
        if self.email_service:
            self.email_service.enviar_verificacao(dados["email"], self.db)

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

        valido = self.sms_service.verificar_codigo(usuario.telefone, codigo, self.db)
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

        self.sms_service.enviar_verificacao(usuario.telefone, self.db)
        return True

    # ── Verificação por e-mail ─────────────────────────────────────────────

    def ativar_conta_email(self, email: str, codigo: str):
        """Valida o código de e-mail e ativa a conta."""
        if not self.email_service:
            raise ValueError("Serviço de e-mail não disponível.")

        usuario = self.db.query(Usuario).filter(Usuario.email == email).first()
        if not usuario:
            raise ValueError("Usuário não encontrado.")

        if usuario.status:
            raise ValueError("Conta já está ativa.")

        valido = self.email_service.verificar_codigo(email, codigo, self.db)
        if not valido:
            raise ValueError("Código inválido ou expirado.")

        usuario.status = True
        self.db.commit()
        self.db.refresh(usuario)
        return usuario

    def reenviar_codigo_email(self, email: str):
        """Reenvia o código de verificação por e-mail."""
        if not self.email_service:
            raise ValueError("Serviço de e-mail não disponível.")

        usuario = self.db.query(Usuario).filter(Usuario.email == email).first()
        if not usuario:
            raise ValueError("Usuário não encontrado.")

        if usuario.status:
            raise ValueError("Conta já está ativa.")

        self.email_service.enviar_verificacao(email, self.db)
        return True

    # ── Verificação de celular (endpoint direto sem conta) ─────────────────

    def enviar_sms_para_numero(self, telefone: str):
        """Envia código SMS para um número avulso (antes do cadastro)."""
        if not self.sms_service:
            raise ValueError("Serviço de SMS não disponível.")
        self.sms_service.enviar_verificacao(telefone, self.db)
        return True

    def verificar_sms_para_numero(self, telefone: str, codigo: str):
        """Valida o código SMS de um número avulso (antes do cadastro)."""
        if not self.sms_service:
            raise ValueError("Serviço de SMS não disponível.")
        valido = self.sms_service.verificar_codigo(telefone, codigo, self.db)
        if not valido:
            raise ValueError("Código inválido ou expirado.")
        return True

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

    def autenticar_ou_criar_google(self, email: str, nome: str):
        # 1. Tenta achar o usuário pelo e-mail
        usuario = self.db.query(Usuario).filter(Usuario.email == email).first()
        
        # 2. Se o usuário não existir, cria um novo automaticamente
        if not usuario:
            usuario = Usuario(
                nome=nome,
                email=email,
                senha_hash=None, # Não tem senha
                telefone=None,   # Não tem telefone inicialmente
                provedor_auth="google",
                status=True      # Usuários do Google já vêm com e-mail validado por eles, então podemos considerar ativo
            )
            self.db.add(usuario)
            self.db.commit()
            self.db.refresh(usuario)
            
        # 3. Se o usuário existe, mas foi criado via login comum (local), atualiza o provedor
        elif usuario.provedor_auth == "local":
            usuario.provedor_auth = "google_local"
            self.db.commit()
            self.db.refresh(usuario)
            
        # 4. Retorna o usuário (novo ou existente)
        return usuario