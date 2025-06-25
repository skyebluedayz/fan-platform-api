# api/support_api.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os
from datetime import datetime

# モデルのインポートのためにパスを追加
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from models.support_models import (
    add_support_transaction,
    get_creator_earnings,
    get_support_history,
    get_user_points,
    update_user_points
)

# 設定ファイルをインポート
try:
    from config import get_config
    config = get_config()
    print(f"Configuration loaded: {type(config).__name__}")
except ImportError:
    print("Warning: config.py not found, using default settings")
    config = None

app = Flask(__name__)

# 設定を適用（config.pyがある場合）
if config:
    app.config.from_object(config)

# 環境に応じたCORS設定
flask_env = os.environ.get('FLASK_ENV', 'development')
if flask_env == 'production':
    # 本番環境：環境変数から許可するオリジンを取得
    cors_origins_str = os.environ.get('CORS_ORIGINS', '')
    if cors_origins_str:
        cors_origins = [origin.strip() for origin in cors_origins_str.split(',') if origin.strip()]
        CORS(app, origins=cors_origins)
        print(f"Production mode: CORS origins = {cors_origins}")
    else:
        CORS(app)
        print("Production mode: CORS origins = all (WARNING: not secure)")
else:
    # 開発環境：localhost:3000のみ許可
    CORS(app, origins=['http://localhost:3000'])
    print("Development mode: CORS origins = ['http://localhost:3000']")

# ヘルスチェックエンドポイント
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'environment': flask_env,
        'version': '1.0.0'
    })

# 支援統計を取得
@app.route('/api/support/stats', methods=['GET'])
def get_support_stats():
    try:
        # 簡単な統計情報を返す
        stats = {
            'total_supporters': 150,
            'total_amount': 45000,
            'active_creators': 25,
            'timestamp': datetime.now().isoformat()
        }
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 支援を追加
@app.route('/api/support/add', methods=['POST'])
def add_support():
    try:
        data = request.get_json()
        
        # 必要なデータの検証
        required_fields = ['user_id', 'creator_id', 'amount']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # 支援取引を追加
        result = add_support_transaction(
            user_id=data['user_id'],
            creator_id=data['creator_id'],
            amount=data['amount'],
            message=data.get('message', '')
        )
        
        if result:
            return jsonify({'success': True, 'message': 'Support added successfully'})
        else:
            return jsonify({'error': 'Failed to add support'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# クリエイターの収益を取得
@app.route('/api/creator/earnings/<int:creator_id>', methods=['GET'])
def get_creator_earnings_api(creator_id):
    try:
        earnings = get_creator_earnings(creator_id)
        return jsonify({
            'creator_id': creator_id,
            'earnings': earnings,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 支援履歴を取得
@app.route('/api/support/history/<int:user_id>', methods=['GET'])
def get_support_history_api(user_id):
    try:
        history = get_support_history(user_id)
        return jsonify({
            'user_id': user_id,
            'history': history,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ユーザーのポイントを取得
@app.route('/api/user/points/<int:user_id>', methods=['GET'])
def get_user_points_api(user_id):
    try:
        points = get_user_points(user_id)
        return jsonify({
            'user_id': user_id,
            'points': points,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ユーザーのポイントを更新
@app.route('/api/user/points/<int:user_id>/update', methods=['POST'])
def update_user_points_api(user_id):
    try:
        data = request.get_json()
        
        if 'points' not in data:
            return jsonify({'error': 'Missing points field'}), 400
        
        result = update_user_points(user_id, data['points'])
        
        if result:
            return jsonify({'success': True, 'message': 'Points updated successfully'})
        else:
            return jsonify({'error': 'Failed to update points'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 全エンドポイント一覧（開発用）
@app.route('/api/endpoints', methods=['GET'])
def list_endpoints():
    endpoints = []
    for rule in app.url_map.iter_rules():
        endpoints.append({
            'endpoint': rule.endpoint,
            'methods': list(rule.methods),
            'url': str(rule)
        })
    return jsonify({'endpoints': endpoints})

# エラーハンドラー
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# メイン実行部分
if __name__ == '__main__':
    print("=" * 50)
    print("🚀 Fan Platform Support API Server")
    print("=" * 50)
    print(f"Environment: {flask_env}")
    print(f"Debug mode: {flask_env != 'production'}")
    print("Available endpoints:")
    print("  GET  /api/health")
    print("  GET  /api/support/stats")
    print("  POST /api/support/add")
    print("  GET  /api/creator/earnings/<creator_id>")
    print("  GET  /api/support/history/<user_id>")
    print("  GET  /api/user/points/<user_id>")
    print("  POST /api/user/points/<user_id>/update")
    print("  GET  /api/endpoints")
    print("=" * 50)
    
    # 本番環境では0.0.0.0、開発環境では127.0.0.1を使用
    host = '0.0.0.0' if flask_env == 'production' else '127.0.0.1'
    port = int(os.environ.get('PORT', 5002))
    debug = flask_env != 'production'
    
    app.run(host=host, port=port, debug=debug)
