# config/database.py
# Phase 2-A データベース設定

import os
from dotenv import load_dotenv

load_dotenv()

class DatabaseConfig:
    """データベース設定クラス"""
    
    # PostgreSQL設定 (Phase 2-A)
    POSTGRES_HOST = os.getenv('DB_HOST', 'localhost')
    POSTGRES_DB = os.getenv('DB_NAME', 'oshikatu')
    POSTGRES_USER = os.getenv('DB_USER', 'postgres')
    POSTGRES_PASSWORD = os.getenv('DB_PASSWORD', '')
    POSTGRES_PORT = os.getenv('DB_PORT', '5432')
    
    # SQLite設定 (Phase 1 互換)
    SQLITE_DB = 'fan_platform.db'
    
    # 使用するデータベース
    USE_POSTGRES = os.getenv('USE_POSTGRES', 'False').lower() == 'true'
    
    @classmethod
    def get_postgres_url(cls):
        """PostgreSQL接続URLを取得"""
        return f"postgresql://{cls.POSTGRES_USER}:{cls.POSTGRES_PASSWORD}@{cls.POSTGRES_HOST}:{cls.POSTGRES_PORT}/{cls.POSTGRES_DB}"
    
    @classmethod
    def get_sqlite_url(cls):
        """SQLite接続URLを取得"""
        return f"sqlite:///{cls.SQLITE_DB}"
