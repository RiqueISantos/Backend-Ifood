from werkzeug.security import generate_password_hash, check_password_hash
from models.models import Usuario

class UsuarioController:
    def __init__(self,db):
        self.db = db

    def gerar_hash(self, senha: str):
        return generate_password_hash(senha)

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

    def autenticar(self, email, senha):
        if not email or not senha:
            raise ValueError("Email e senha são obrigatórios.")

        usuario = self.db.query(Usuario).filter(Usuario.email == email).first()

        if usuario and check_password_hash(usuario.senha_hash, senha):
            return usuario
            
        return None

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


    def atualizar(self, usuario_id: int,dados):
        usuario = self.db.query(Usuario).filter(Usuario.id == usuario_id).first()
        if not usuario:
            raise ValueError(
                "Usuário não encontrado."
            )


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
                    provedor_auth="google"
                )
                self.db.add(usuario)
                self.db.commit()
                self.db.refresh(usuario)
                
            # 3. Retorna o usuário (novo ou existente)
            return usuario
