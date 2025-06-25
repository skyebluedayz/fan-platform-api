# api/file_api.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from sqlalchemy.orm import sessionmaker
from models.creator_models import engine, SessionLocal
from models.file_models import File, FileCategory, FileTag
from utils.file_handler import FileUploadHandler, process_file_upload
import json
from datetime import datetime

app = Flask(__name__)
CORS(app)

# ファイルアップロードハンドラー
file_handler = FileUploadHandler()

def get_db():
    """データベースセッション取得"""
    db = SessionLocal()
    try:
        return db
    finally:
        pass

# ===============================
# ファイルカテゴリAPI
# ===============================

@app.route('/api/file-categories', methods=['GET'])
def get_file_categories():
    """ファイルカテゴリ一覧取得"""
    db = get_db()
    try:
        categories = db.query(FileCategory).all()
        result = []
        for cat in categories:
            allowed_ext = json.loads(cat.allowed_extensions) if cat.allowed_extensions else []
            result.append({
                'id': cat.id,
                'name': cat.name,
                'description': cat.description,
                'allowed_extensions': allowed_ext,
                'max_size_mb': cat.max_size_mb,
                'file_count': len(cat.files)
            })
        return jsonify({'categories': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

# ===============================
# ファイル一覧API
# ===============================

@app.route('/api/files', methods=['GET'])
def get_files():
    """ファイル一覧取得（検索・フィルタ対応）"""
    db = get_db()
    try:
        query = db.query(File)
        
        # 検索フィルタ
        search = request.args.get('search')
        if search:
            query = query.filter(
                File.title.contains(search) |
                File.description.contains(search) |
                File.original_name.contains(search)
            )
        
        # カテゴリフィルタ
        category_id = request.args.get('category_id')
        if category_id:
            query = query.filter(File.category_id == category_id)
        
        # ページング
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 12))
        files = query.offset((page - 1) * per_page).limit(per_page).all()
        
        result = []
        for file in files:
            result.append({
                'id': file.id,
                'filename': file.filename,
                'original_name': file.original_name,
                'title': file.title or file.original_name,
                'description': file.description,
                'file_type': file.file_type,
                'file_size': file.file_size,
                'category': {
                    'id': file.category.id,
                    'name': file.category.name
                } if file.category else None,
                'url': f'/api/files/{file.id}',
                'created_at': file.created_at.isoformat()
            })
        
        return jsonify({
            'files': result,
            'page': page,
            'per_page': per_page
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

# ===============================
# ファイル詳細API
# ===============================

@app.route('/api/files/<int:file_id>', methods=['GET'])
def get_file_detail(file_id):
    """ファイル詳細取得"""
    db = get_db()
    try:
        file = db.query(File).filter(File.id == file_id).first()
        if not file:
            return jsonify({'error': 'ファイルが見つかりません'}), 404
        
        return jsonify({
            'file': {
                'id': file.id,
                'filename': file.filename,
                'original_name': file.original_name,
                'title': file.title or file.original_name,
                'description': file.description,
                'file_type': file.file_type,
                'file_size': file.file_size,
                'width': file.width,
                'height': file.height,
                'category': {
                    'id': file.category.id,
                    'name': file.category.name
                } if file.category else None,
                'created_at': file.created_at.isoformat()
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

# ===============================
# API テスト用
# ===============================

@app.route('/api/files/test', methods=['GET'])
def test_file_api():
    """ファイルAPI動作テスト"""
    return jsonify({
        'message': '🗂️ Phase 2-B ファイル管理API は正常に動作しています！',
        'timestamp': datetime.utcnow().isoformat(),
        'available_endpoints': [
            'GET /api/file-categories - ファイルカテゴリ一覧',
            'GET /api/files - ファイル一覧・検索',
            'GET /api/files/{id} - ファイル詳細'
        ]
    })

if __name__ == '__main__':
    print("🗂️ OshiKatu ファイル管理API サーバーを起動中...")
    app.run(debug=True, port=5001, host='0.0.0.0')
