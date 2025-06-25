from database import engine
from models import Base

# モデルで定義したテーブルを全て作成
Base.metadata.create_all(bind=engine)

print("✅ データベースの初期化が完了しました")
