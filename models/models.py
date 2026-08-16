from datetime import datetime
from sqlalchemy import Column, BigInteger, String, DateTime
from database import Base

class Usuario(Base):
    __tablename__ = 'usuarios'

    id = Column(BigInteger,primary_key=True,autoincrement=True)
    nome = Column(String(100), nullable=False)
    email = Column(String(150), nullable=False, unique=True)
    telefone = Column(String(20), nullable=True)
    senha_hash = Column(String(255), nullable=True)
    provedor_auth = Column(String(20), nullable=True, default="local")
    data_criacao = Column(DateTime, default=datetime.utcnow, nullable=False)

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