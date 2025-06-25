from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

# SQLite用のデータベースURL（./ は現在のフォルダの意味）
# ✅ ファイル名を users.db → fan_platform.db に修正
SQLALCHEMY_DATABASE_URL = "sqlite:///./fan_platform.db"

# データベースエンジンの作成
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# セッションローカルの作成（DB接続の窓口）
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ベースクラスの作成（これを使ってモデルを作る）
Base = declarative_base()

# 依存性注入用のヘルパー関数（main.pyで使用）
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()