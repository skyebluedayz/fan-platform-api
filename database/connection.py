# database/connection.py
# Phase 2-A データベース接続管理

import psycopg2
import sqlite3
import os
from config.database import DatabaseConfig

def get_postgres_connection():
    """PostgreSQL接続を取得"""
    try:
        connection = psycopg2.connect(
            host=DatabaseConfig.POSTGRES_HOST,
            database=DatabaseConfig.POSTGRES_DB,
            user=DatabaseConfig.POSTGRES_USER,
            password=DatabaseConfig.POSTGRES_PASSWORD,
            port=DatabaseConfig.POSTGRES_PORT
        )
        return connection
    except Exception as e:
        print(f"❌ PostgreSQL接続エラー: {e}")
        raise

def get_sqlite_connection():
    """SQLite接続を取得（Phase 1互換）"""
    try:
        connection = sqlite3.connect(DatabaseConfig.SQLITE_DB)
        return connection
    except Exception as e:
        print(f"❌ SQLite接続エラー: {e}")
        raise

def get_connection():
    """設定に応じてデータベース接続を取得"""
    if DatabaseConfig.USE_POSTGRES:
        return get_postgres_connection()
    else:
        return get_sqlite_connection()

def test_connections():
    """両方のデータベース接続をテスト"""
    print("🔍 データベース接続テスト")
    print("-" * 30)
    
    # SQLite接続テスト
    try:
        sqlite_conn = get_sqlite_connection()
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT sqlite_version();")
        version = cursor.fetchone()
        cursor.close()
        sqlite_conn.close()
        print(f"✅ SQLite接続成功: {version[0]}")
    except Exception as e:
        print(f"❌ SQLite接続失敗: {e}")
    
    # PostgreSQL接続テスト（.envでUSE_POSTGRES=Trueの場合のみ）
    if DatabaseConfig.USE_POSTGRES:
        try:
            postgres_conn = get_postgres_connection()
            cursor = postgres_conn.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            cursor.close()
            postgres_conn.close()
            print(f"✅ PostgreSQL接続成功")
        except Exception as e:
            print(f"❌ PostgreSQL接続失敗: {e}")
            print("   PostgreSQLが起動していない、または設定が間違っている可能性があります")
    else:
        print("ℹ️  PostgreSQLテストはスキップ (USE_POSTGRES=False)")

if __name__ == "__main__":
    test_connections()
