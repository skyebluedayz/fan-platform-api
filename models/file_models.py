# models/file_models.py
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import os

# 既存のBaseを継承
from models.creator_models import Base, User, Creator

class FileCategory(Base):
    """ファイルカテゴリテーブル"""
    __tablename__ = 'file_categories'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    allowed_extensions = Column(Text)  # JSON文字列: [".jpg", ".png", ".mp4"]
    max_size_mb = Column(Float, default=50.0)  # 最大ファイルサイズ(MB)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # リレーション
    files = relationship("File", back_populates="category")

class File(Base):
    """ファイルテーブル"""
    __tablename__ = 'files'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    creator_id = Column(Integer, ForeignKey('creators.id'), nullable=True)  # 関連クリエイター
    category_id = Column(Integer, ForeignKey('file_categories.id'), nullable=False)
    
    # ファイル情報
    filename = Column(String(255), nullable=False)  # 保存時のファイル名
    original_name = Column(String(255), nullable=False)  # 元のファイル名
    file_type = Column(String(50), nullable=False)  # MIME type
    file_extension = Column(String(10), nullable=False)  # .jpg, .png等
    file_size = Column(Integer, nullable=False)  # バイト単位
    file_path = Column(String(500), nullable=False)  # ファイル保存パス
    
    # メタデータ
    title = Column(String(200))  # ユーザー設定のタイトル
    description = Column(Text)  # ファイル説明
    alt_text = Column(String(500))  # アクセシビリティ用代替テキスト
    
    # 画像固有メタデータ
    width = Column(Integer)  # 画像幅
    height = Column(Integer)  # 画像高さ
    
    # 動画固有メタデータ
    duration = Column(Float)  # 動画長（秒）
    
    # 公開設定
    is_public = Column(Boolean, default=False)
    is_featured = Column(Boolean, default=False)  # 注目作品フラグ
    
    # 統計
    view_count = Column(Integer, default=0)
    download_count = Column(Integer, default=0)
    
    # 日時
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # リレーション
    owner = relationship("User", back_populates="files")
    creator = relationship("Creator", back_populates="files")
    category = relationship("FileCategory", back_populates="files")
    tags = relationship("FileTag", back_populates="file")

class FileTag(Base):
    """ファイルタグテーブル（ファイル固有のタグ）"""
    __tablename__ = 'file_tags'
    
    id = Column(Integer, primary_key=True)
    file_id = Column(Integer, ForeignKey('files.id'), nullable=False)
    tag_name = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # リレーション
    file = relationship("File", back_populates="tags")

# 既存モデルにリレーション追加
User.files = relationship("File", back_populates="owner")
Creator.files = relationship("File", back_populates="creator")

# デフォルトファイルカテゴリ
DEFAULT_FILE_CATEGORIES = [
    {
        "name": "イラスト",
        "description": "デジタルイラスト、手描き作品",
        "allowed_extensions": [".jpg", ".jpeg", ".png", ".gif", ".webp"],
        "max_size_mb": 10.0
    },
    {
        "name": "写真",
        "description": "写真作品、ポートレート",
        "allowed_extensions": [".jpg", ".jpeg", ".png", ".tiff", ".raw"],
        "max_size_mb": 25.0
    },
    {
        "name": "動画",
        "description": "ショート動画、作品紹介",
        "allowed_extensions": [".mp4", ".mov", ".avi", ".webm"],
        "max_size_mb": 100.0
    },
    {
        "name": "音楽",
        "description": "楽曲、ボイス作品",
        "allowed_extensions": [".mp3", ".wav", ".m4a", ".flac"],
        "max_size_mb": 50.0
    },
    {
        "name": "文書",
        "description": "PDF、テキスト文書",
        "allowed_extensions": [".pdf", ".txt", ".doc", ".docx"],
        "max_size_mb": 20.0
    },
    {
        "name": "その他",
        "description": "その他のファイル",
        "allowed_extensions": [".zip", ".rar", ".psd", ".ai"],
        "max_size_mb": 100.0
    }
]

def create_file_tables():
    """ファイル管理用テーブル作成"""
    from models.creator_models import engine
    Base.metadata.create_all(bind=engine)
    print("✅ Phase 2-B ファイル管理テーブル作成完了！")

def init_file_categories():
    """デフォルトファイルカテゴリを挿入"""
    from models.creator_models import SessionLocal
    import json
    
    db = SessionLocal()
    try:
        for cat_data in DEFAULT_FILE_CATEGORIES:
            existing = db.query(FileCategory).filter_by(name=cat_data["name"]).first()
            if not existing:
                category = FileCategory(
                    name=cat_data["name"],
                    description=cat_data["description"],
                    allowed_extensions=json.dumps(cat_data["allowed_extensions"]),
                    max_size_mb=cat_data["max_size_mb"]
                )
                db.add(category)
        
        db.commit()
        print("✅ デフォルトファイルカテゴリ挿入完了！")
    except Exception as e:
        print(f"❌ エラー: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_file_tables()
    init_file_categories()
