from datetime import datetime
from sqlalchemy import Column, BigInteger, String, DateTime, Boolean, Float
from database import Base

class SmsVerificacao(Base):
    __tablename__ = 'sms_verificacoes'

    id       = Column(BigInteger, primary_key=True, autoincrement=True)
    numero   = Column(String(20),  nullable=False, index=True)
    codigo   = Column(String(6),   nullable=False)
    expira_em = Column(Float,      nullable=False)   # unix timestamp
    verificado = Column(Boolean,   default=False)
    verificado_expira_em = Column(Float, nullable=True)  # unix timestamp da janela pós-verificação

class EmailVerificacao(Base):
    __tablename__ = 'email_verificacoes'

    id        = Column(BigInteger, primary_key=True, autoincrement=True)
    email     = Column(String(150), nullable=False, index=True)
    codigo    = Column(String(6),   nullable=False)
    expira_em = Column(Float,       nullable=False)  # unix timestamp

class Usuario(Base):
    __tablename__ = 'usuarios'

    id = Column(BigInteger,primary_key=True,autoincrement=True)
    nome = Column(String(100), nullable=False)
    email = Column(String(150), nullable=False, unique=True)
    telefone = Column(String(20), nullable=True)
    senha_hash = Column(String(255), nullable=True)
    provedor_auth = Column(String(20), nullable=True, default="local")
    data_criacao = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(Boolean, default=False)

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "email": self.email,
            "telefone": self.telefone,
            "provedor_auth": self.provedor_auth,
            "data_criacao": self.data_criacao.isoformat() if self.data_criacao else None
        }

    def __repr__(self):
        return f"<Usuario(id={self.id}, nome='{self.nome}', email='{self.email}')>"