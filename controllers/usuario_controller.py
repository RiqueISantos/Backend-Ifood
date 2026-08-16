import hashlib
from models.models import Usuario

class UsuarioController:
    def __init__(self,db):
        self.db = db

    def gerar_hash(self, senha:str):
        return hashlib.sha256(senha.encode()).hexdigest()

    def cadastrar(self, dados):
        if not dados.get("nome") or not dados.get("email") or not dados.get("senha") or not dados.get("telefone"):
            raise ValueError('Dados obrigatórios não preenchidos.')

        if self.db.query(Usuario).filter(Usuario.email == dados["email"]).first():
            raise ValueError("Email já cadastrado.")

        novo_usuario = Usuario(
            nome=dados["nome"],
            email=dados["email"],
            senha_hash = self.gerar_hash(dados["senha"]),
            telefone = dados.get("telefone"),
            provedor_auth= dados.get("provedor_auth","local")
        )

        self.db.add(novo_usuario)
        self.db.commit()
        self.db.refresh(novo_usuario)
        return novo_usuario

    def autenticar(self,email,senha):
        if not email or not senha:
            raise ValueError("Email e senha são obrigatórios.")

        senha_hash = self.gerar_hash(senha)
        usuario = self.db.query(Usuario).filter(
            Usuario.email == email,
            Usuario.senha_hash == senha_hash
        ).first()
        return usuario

    def buscar_usuario(self, usuario_email):
        usuario = self.db.query(Usuario).filter(Usuario.email == usuario_email).first()
        if not usuario:
            raise ValueError("Usuário não encontrado.")
        return usuario