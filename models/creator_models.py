# models/creator_models.py
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Table, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()

# 中間テーブル：クリエイターとカテゴリの多対多関係
creator_categories = Table('creator_categories', Base.metadata,
    Column('creator_id', Integer, ForeignKey('creators.id'), primary_key=True),
    Column('category_id', Integer, ForeignKey('categories.id'), primary_key=True)
)

# 中間テーブル：クリエイターとタグの多対多関係
creator_tags = Table('creator_tags', Base.metadata,
    Column('creator_id', Integer, ForeignKey('creators.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id'), primary_key=True)
)

class User(Base):
    """既存のユーザーモデル（Phase 1から継続）"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    points = Column(Integer, default=1000)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # リレーション
    created_creators = relationship("Creator", back_populates="owner")
    favorites = relationship("UserFavorite", back_populates="user")

class Creator(Base):
    """クリエイター情報テーブル"""
    __tablename__ = 'creators'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    profile_image = Column(String(255))
    social_links = Column(Text)  # JSON文字列として保存
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # リレーション
    owner = relationship("User", back_populates="created_creators")
    categories = relationship("Category", secondary=creator_categories, back_populates="creators")
    tags = relationship("Tag", secondary=creator_tags, back_populates="creators")
    favorites = relationship("UserFavorite", back_populates="creator")

class Category(Base):
    """カテゴリテーブル"""
    __tablename__ = 'categories'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    color = Column(String(7))  # HEXカラーコード #FFFFFF
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # リレーション
    creators = relationship("Creator", secondary=creator_categories, back_populates="categories")

class Tag(Base):
    """タグテーブル"""
    __tablename__ = 'tags'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(30), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # リレーション
    creators = relationship("Creator", secondary=creator_tags, back_populates="tags")

class UserFavorite(Base):
    """ユーザーの推しリスト（お気に入りクリエイター）"""
    __tablename__ = 'user_favorites'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    creator_id = Column(Integer, ForeignKey('creators.id'), nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow)
    
    # リレーション
    user = relationship("User", back_populates="favorites")
    creator = relationship("Creator", back_populates="favorites")

# データベース接続とセッション管理
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///oshikatu.db')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    """データベーステーブルを作成"""
    Base.metadata.create_all(bind=engine)
    print("✅ データベーステーブル作成完了！")

def get_db():
    """データベースセッション取得"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# デフォルトカテゴリとタグ
DEFAULT_CATEGORIES = [
    {"name": "イラストレーター", "description": "イラスト・アート作品を作成", "color": "#FF6B9D"},
    {"name": "Vtuber", "description": "バーチャルYouTuber・配信者", "color": "#A78BFA"},
    {"name": "歌い手", "description": "歌・音楽系クリエイター", "color": "#60A5FA"},
    {"name": "写真家", "description": "写真・撮影系クリエイター", "color": "#34D399"},
    {"name": "ゲーマー", "description": "ゲーム実況・攻略系", "color": "#FBBF24"},
    {"name": "その他", "description": "その他のクリエイター", "color": "#9CA3AF"}
]

DEFAULT_TAGS = [
    "可愛い", "かっこいい", "癒し", "面白い", "上手", 
    "推せる", "応援したい", "才能", "努力家", "個性的"
]

def init_default_data():
    """デフォルトデータを挿入"""
    db = SessionLocal()
    try:
        # カテゴリ作成
        for cat_data in DEFAULT_CATEGORIES:
            existing = db.query(Category).filter_by(name=cat_data["name"]).first()
            if not existing:
                category = Category(**cat_data)
                db.add(category)
        
        # タグ作成
        for tag_name in DEFAULT_TAGS:
            existing = db.query(Tag).filter_by(name=tag_name).first()
            if not existing:
                tag = Tag(name=tag_name)
                db.add(tag)
        
        db.commit()
        print("✅ デフォルトデータ挿入完了！")
    except Exception as e:
        print(f"❌ エラー: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_tables()
    init_default_data()
