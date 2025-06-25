# models/support_models.py
import sqlite3
from datetime import datetime
import os

# データベースファイルのパス
DB_PATH = './models/fan_platform.db'

def init_support_db():
    """支援機能用のテーブルを作成"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 1. 支援取引テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS support_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                creator_id INTEGER NOT NULL,
                points_amount INTEGER NOT NULL,
                message TEXT,
                transaction_type TEXT DEFAULT 'support',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (creator_id) REFERENCES creators (id)
            )
        ''')
        
        # 2. クリエイター収益テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS creator_earnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_id INTEGER NOT NULL,
                total_points_received INTEGER DEFAULT 0,
                total_supporters INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (creator_id) REFERENCES creators (id),
                UNIQUE(creator_id)
            )
        ''')
        
        # 3. ユーザーポイント履歴テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_point_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                points_change INTEGER NOT NULL,
                balance_after INTEGER NOT NULL,
                transaction_type TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        print("✅ 支援機能テーブルが正常に作成されました")
        
    except Exception as e:
        print(f"❌ テーブル作成エラー: {e}")
        conn.rollback()
    finally:
        conn.close()

def add_support_transaction(user_id, creator_id, points_amount, message=""):
    """支援取引を記録"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 支援取引を記録
        cursor.execute('''
            INSERT INTO support_transactions (user_id, creator_id, points_amount, message)
            VALUES (?, ?, ?, ?)
        ''', (user_id, creator_id, points_amount, message))
        
        # クリエイター収益を更新
        cursor.execute('''
            INSERT OR REPLACE INTO creator_earnings (creator_id, total_points_received, total_supporters, last_updated)
            VALUES (?, 
                    COALESCE((SELECT total_points_received FROM creator_earnings WHERE creator_id = ?), 0) + ?,
                    (SELECT COUNT(DISTINCT user_id) FROM support_transactions WHERE creator_id = ?),
                    CURRENT_TIMESTAMP)
        ''', (creator_id, creator_id, points_amount, creator_id))
        
        # ユーザーポイント履歴を記録
        cursor.execute('''
            INSERT INTO user_point_history (user_id, points_change, balance_after, transaction_type, description)
            VALUES (?, ?, 
                    (SELECT points FROM users WHERE id = ?) - ?,
                    'support', ?)
        ''', (user_id, -points_amount, user_id, points_amount, f"クリエイターID {creator_id} への支援"))
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"❌ 支援取引記録エラー: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def get_creator_earnings(creator_id):
    """クリエイターの収益情報を取得"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT ce.total_points_received, ce.total_supporters, ce.last_updated,
                   COUNT(st.id) as total_transactions
            FROM creator_earnings ce
            LEFT JOIN support_transactions st ON ce.creator_id = st.creator_id
            WHERE ce.creator_id = ?
            GROUP BY ce.creator_id
        ''', (creator_id,))
        
        result = cursor.fetchone()
        if result:
            return {
                'total_points_received': result[0],
                'total_supporters': result[1],
                'last_updated': result[2],
                'total_transactions': result[3]
            }
        else:
            return {
                'total_points_received': 0,
                'total_supporters': 0,
                'last_updated': None,
                'total_transactions': 0
            }
            
    except Exception as e:
        print(f"❌ 収益情報取得エラー: {e}")
        return None
    finally:
        conn.close()

def get_support_history(user_id=None, creator_id=None, limit=50):
    """支援履歴を取得"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        if user_id:
            # ユーザーの支援履歴
            cursor.execute('''
                SELECT st.*, c.name as creator_name
                FROM support_transactions st
                JOIN creators c ON st.creator_id = c.id
                WHERE st.user_id = ?
                ORDER BY st.created_at DESC
                LIMIT ?
            ''', (user_id, limit))
        elif creator_id:
            # クリエイターが受けた支援履歴
            cursor.execute('''
                SELECT st.*, u.username as supporter_name
                FROM support_transactions st
                LEFT JOIN users u ON st.user_id = u.id
                WHERE st.creator_id = ?
                ORDER BY st.created_at DESC
                LIMIT ?
            ''', (creator_id, limit))
        else:
            # 全体の支援履歴
            cursor.execute('''
                SELECT st.*, c.name as creator_name
                FROM support_transactions st
                JOIN creators c ON st.creator_id = c.id
                ORDER BY st.created_at DESC
                LIMIT ?
            ''', (limit,))
        
        results = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        return [dict(zip(columns, row)) for row in results]
        
    except Exception as e:
        print(f"❌ 支援履歴取得エラー: {e}")
        return []
    finally:
        conn.close()

def get_user_points(user_id):
    """ユーザーの現在のポイントを取得"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT points FROM users WHERE id = ?', (user_id,))
        result = cursor.fetchone()
        return result[0] if result else 0
        
    except Exception as e:
        print(f"❌ ポイント取得エラー: {e}")
        return 0
    finally:
        conn.close()

def update_user_points(user_id, new_points):
    """ユーザーのポイントを更新"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('UPDATE users SET points = ? WHERE id = ?', (new_points, user_id))
        conn.commit()
        return True
        
    except Exception as e:
        print(f"❌ ポイント更新エラー: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    # テスト実行
    init_support_db()
    print("支援機能データベースの初期化が完了しました！")# models/support_models.py
import sqlite3
from datetime import datetime
import os

# データベースファイルのパス
DB_PATH = 'fan_platform.db'

def init_support_db():
    """支援機能用のテーブルを作成"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 1. 支援取引テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS support_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                creator_id INTEGER NOT NULL,
                points_amount INTEGER NOT NULL,
                message TEXT,
                transaction_type TEXT DEFAULT 'support',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (creator_id) REFERENCES creators (id)
            )
        ''')
        
        # 2. クリエイター収益テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS creator_earnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_id INTEGER NOT NULL,
                total_points_received INTEGER DEFAULT 0,
                total_supporters INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (creator_id) REFERENCES creators (id),
                UNIQUE(creator_id)
            )
        ''')
        
        # 3. ユーザーポイント履歴テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_point_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                points_change INTEGER NOT NULL,
                balance_after INTEGER NOT NULL,
                transaction_type TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        print("✅ 支援機能テーブルが正常に作成されました")
        
    except Exception as e:
        print(f"❌ テーブル作成エラー: {e}")
        conn.rollback()
    finally:
        conn.close()

def add_support_transaction(user_id, creator_id, points_amount, message=""):
    """支援取引を記録"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 支援取引を記録
        cursor.execute('''
            INSERT INTO support_transactions (user_id, creator_id, points_amount, message)
            VALUES (?, ?, ?, ?)
        ''', (user_id, creator_id, points_amount, message))
        
        # クリエイター収益を更新
        cursor.execute('''
            INSERT OR REPLACE INTO creator_earnings (creator_id, total_points_received, total_supporters, last_updated)
            VALUES (?, 
                    COALESCE((SELECT total_points_received FROM creator_earnings WHERE creator_id = ?), 0) + ?,
                    (SELECT COUNT(DISTINCT user_id) FROM support_transactions WHERE creator_id = ?),
                    CURRENT_TIMESTAMP)
        ''', (creator_id, creator_id, points_amount, creator_id))
        
        # ユーザーポイント履歴を記録
        cursor.execute('''
            INSERT INTO user_point_history (user_id, points_change, balance_after, transaction_type, description)
            VALUES (?, ?, 
                    (SELECT points FROM users WHERE id = ?) - ?,
                    'support', ?)
        ''', (user_id, -points_amount, user_id, points_amount, f"クリエイターID {creator_id} への支援"))
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"❌ 支援取引記録エラー: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def get_creator_earnings(creator_id):
    """クリエイターの収益情報を取得"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT ce.total_points_received, ce.total_supporters, ce.last_updated,
                   COUNT(st.id) as total_transactions
            FROM creator_earnings ce
            LEFT JOIN support_transactions st ON ce.creator_id = st.creator_id
            WHERE ce.creator_id = ?
            GROUP BY ce.creator_id
        ''', (creator_id,))
        
        result = cursor.fetchone()
        if result:
            return {
                'total_points_received': result[0],
                'total_supporters': result[1],
                'last_updated': result[2],
                'total_transactions': result[3]
            }
        else:
            return {
                'total_points_received': 0,
                'total_supporters': 0,
                'last_updated': None,
                'total_transactions': 0
            }
            
    except Exception as e:
        print(f"❌ 収益情報取得エラー: {e}")
        return None
    finally:
        conn.close()

def get_support_history(user_id=None, creator_id=None, limit=50):
    """支援履歴を取得"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        if user_id:
            # ユーザーの支援履歴
            cursor.execute('''
                SELECT st.*, c.name as creator_name
                FROM support_transactions st
                JOIN creators c ON st.creator_id = c.id
                WHERE st.user_id = ?
                ORDER BY st.created_at DESC
                LIMIT ?
            ''', (user_id, limit))
        elif creator_id:
            # クリエイターが受けた支援履歴
            cursor.execute('''
                SELECT st.*, u.username as supporter_name
                FROM support_transactions st
                LEFT JOIN users u ON st.user_id = u.id
                WHERE st.creator_id = ?
                ORDER BY st.created_at DESC
                LIMIT ?
            ''', (creator_id, limit))
        else:
            # 全体の支援履歴
            cursor.execute('''
                SELECT st.*, c.name as creator_name
                FROM support_transactions st
                JOIN creators c ON st.creator_id = c.id
                ORDER BY st.created_at DESC
                LIMIT ?
            ''', (limit,))
        
        results = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        return [dict(zip(columns, row)) for row in results]
        
    except Exception as e:
        print(f"❌ 支援履歴取得エラー: {e}")
        return []
    finally:
        conn.close()

def get_user_points(user_id):
    """ユーザーの現在のポイントを取得"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT points FROM users WHERE id = ?', (user_id,))
        result = cursor.fetchone()
        return result[0] if result else 0
        
    except Exception as e:
        print(f"❌ ポイント取得エラー: {e}")
        return 0
    finally:
        conn.close()

def update_user_points(user_id, new_points):
    """ユーザーのポイントを更新"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('UPDATE users SET points = ? WHERE id = ?', (new_points, user_id))
        conn.commit()
        return True
        
    except Exception as e:
        print(f"❌ ポイント更新エラー: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    # テスト実行
    init_support_db()
    print("支援機能データベースの初期化が完了しました！")
