from flask import Flask, request, jsonify
from flask_cors import CORS
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Table, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import json
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# データベース設定
Base = declarative_base()
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///oshikatu.db')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 中間テーブル
creator_categories = Table('creator_categories', Base.metadata,
    Column('creator_id', Integer, ForeignKey('creators.id'), primary_key=True),
    Column('category_id', Integer, ForeignKey('categories.id'), primary_key=True)
)

creator_tags = Table('creator_tags', Base.metadata,
    Column('creator_id', Integer, ForeignKey('creators.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id'), primary_key=True)
)

# モデル定義
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    points = Column(Integer, default=1000)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_creators = relationship("Creator", back_populates="owner")
    favorites = relationship("UserFavorite", back_populates="user")

class Creator(Base):
    __tablename__ = 'creators'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    profile_image = Column(String(255))
    social_links = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    owner = relationship("User", back_populates="created_creators")
    categories = relationship("Category", secondary=creator_categories, back_populates="creators")
    tags = relationship("Tag", secondary=creator_tags, back_populates="creators")
    favorites = relationship("UserFavorite", back_populates="creator")

class Category(Base):
    __tablename__ = 'categories'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    color = Column(String(7))
    created_at = Column(DateTime, default=datetime.utcnow)
    creators = relationship("Creator", secondary=creator_categories, back_populates="categories")

class Tag(Base):
    __tablename__ = 'tags'
    id = Column(Integer, primary_key=True)
    name = Column(String(30), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    creators = relationship("Creator", secondary=creator_tags, back_populates="tags")

class UserFavorite(Base):
    __tablename__ = 'user_favorites'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    creator_id = Column(Integer, ForeignKey('creators.id'), nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="favorites")
    creator = relationship("Creator", back_populates="favorites")

# API エンドポイント
@app.route('/api/test', methods=['GET'])
def test_api():
    return jsonify({
        'message': '🎯 Phase 2-A API は正常に動作しています！',
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/api/categories', methods=['GET'])
def get_categories():
    db = SessionLocal()
    try:
        categories = db.query(Category).all()
        result = []
        for cat in categories:
            result.append({
                'id': cat.id,
                'name': cat.name,
                'description': cat.description,
                'color': cat.color
            })
        return jsonify({'categories': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

if __name__ == '__main__':
    print("🚀 OshiKatu API サーバーを起動中...")
    app.run(debug=True, port=5000, host='0.0.0.0')
