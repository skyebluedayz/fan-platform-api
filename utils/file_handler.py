# utils/file_handler.py
import os
import uuid
import mimetypes
from datetime import datetime
from werkzeug.utils import secure_filename

class FileUploadHandler:
    """ファイルアップロード処理クラス"""
    
    def __init__(self, upload_folder='uploads'):
        self.upload_folder = upload_folder
        self.allowed_extensions = {
            'image': ['.jpg', '.jpeg', '.png', '.gif', '.webp'],
            'video': ['.mp4', '.mov', '.avi', '.webm'],
            'audio': ['.mp3', '.wav', '.m4a', '.flac'],
            'document': ['.pdf', '.txt', '.doc', '.docx'],
            'archive': ['.zip', '.rar', '.psd', '.ai']
        }
        self.max_file_size = 100 * 1024 * 1024  # 100MB
        
        # アップロードフォルダ作成
        self._create_upload_directories()
    
    def _create_upload_directories(self):
        """アップロードディレクトリ構造を作成"""
        directories = [
            self.upload_folder,
            os.path.join(self.upload_folder, 'images'),
            os.path.join(self.upload_folder, 'videos'),
            os.path.join(self.upload_folder, 'audio'),
            os.path.join(self.upload_folder, 'documents'),
            os.path.join(self.upload_folder, 'others'),
            os.path.join(self.upload_folder, 'thumbnails')
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def validate_file(self, file, category_id=None):
        """ファイルバリデーション"""
        errors = []
        
        # ファイル存在チェック
        if not file or file.filename == '':
            errors.append("ファイルが選択されていません")
            return errors, None
        
        # ファイル名の安全性チェック
        filename = secure_filename(file.filename)
        if not filename:
            errors.append("無効なファイル名です")
            return errors, None
        
        # 拡張子チェック
        file_ext = os.path.splitext(filename)[1].lower()
        if not self._is_allowed_extension(file_ext):
            errors.append(f"サポートされていないファイル形式です: {file_ext}")
        
        # ファイルサイズチェック（ここでは概算）
        file.seek(0, 2)  # ファイル末尾へ
        file_size = file.tell()
        file.seek(0)  # ファイル先頭に戻る
        
        if file_size > self.max_file_size:
            errors.append(f"ファイルサイズが大きすぎます（最大: {self.max_file_size // (1024*1024)}MB）")
        
        file_info = {
            'original_name': file.filename,
            'safe_filename': filename,
            'file_extension': file_ext,
            'file_size': file_size,
            'mime_type': mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        }
        
        return errors, file_info
    
    def _is_allowed_extension(self, extension):
        """許可された拡張子かチェック"""
        for ext_list in self.allowed_extensions.values():
            if extension in ext_list:
                return True
        return False
    
    def _get_file_category(self, extension):
        """拡張子からファイルカテゴリを判定"""
        for category, extensions in self.allowed_extensions.items():
            if extension in extensions:
                return category
        return 'others'
    
    def save_file(self, file, user_id, file_info):
        """ファイルを保存"""
        try:
            # ユニークなファイル名生成
            unique_filename = f"{uuid.uuid4().hex}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{file_info['file_extension']}"
            
            # カテゴリ別サブディレクトリ
            category = self._get_file_category(file_info['file_extension'])
            if category == 'image':
                subfolder = 'images'
            elif category == 'video':
                subfolder = 'videos'
            elif category == 'audio':
                subfolder = 'audio'
            elif category == 'document':
                subfolder = 'documents'
            else:
                subfolder = 'others'
            
            # ファイルパス
            file_path = os.path.join(self.upload_folder, subfolder, unique_filename)
            
            # ファイル保存
            file.save(file_path)
            
            # メタデータ取得
            metadata = {'width': None, 'height': None, 'duration': None}
            
            return {
                'success': True,
                'filename': unique_filename,
                'file_path': file_path,
                'thumbnail_path': None,
                'metadata': metadata
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

def process_file_upload(file, user_id, title="", description="", creator_id=None):
    """ファイルアップロード処理のメイン関数"""
    handler = FileUploadHandler()
    
    # バリデーション
    errors, file_info = handler.validate_file(file)
    if errors:
        return {
            'success': False,
            'errors': errors
        }
    
    # ファイル保存
    save_result = handler.save_file(file, user_id, file_info)
    if not save_result['success']:
        return {
            'success': False,
            'errors': [save_result['error']]
        }
    
    # データベース保存用の情報を返す
    return {
        'success': True,
        'file_data': {
            'filename': save_result['filename'],
            'original_name': file_info['original_name'],
            'file_type': file_info['mime_type'],
            'file_extension': file_info['file_extension'],
            'file_size': file_info['file_size'],
            'file_path': save_result['file_path'],
            'width': save_result['metadata']['width'],
            'height': save_result['metadata']['height'],
            'duration': save_result['metadata']['duration'],
            'title': title,
            'description': description
        }
    }
