import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

# Usa variável de ambiente quando disponível (Docker), senão cai no padrão local
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password123@localhost:5432/db_ifood"
)

engine = create_engine(
    DATABASE_URL,
    echo=True,
    pool_pre_ping=True,       # testa a conexão antes de usar, reconecta se estiver morta
    pool_recycle=1800,        # recicla conexões a cada 30 minutos
    pool_size=5,
    max_overflow=10,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
