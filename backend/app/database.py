from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# 載入 .env 檔案中的環境變數
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./health_app.db")
# SQLALCHEMY_DATABASE_URL = "postgresql://user:password@postgresserver/db" # Example for PostgreSQL

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    # connect_args 是 SQLite 特有的設定
    connect_args={"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
