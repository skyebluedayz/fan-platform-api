# models.py - 既存コードの最小限修正版
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

# プラットフォーム手数料を定数として定義（15%固定）
PLATFORM_FEE_RATE = 0.15

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=False)
    is_creator_verified = Column(Boolean, default=False)
    
    # 収益・支援統計
    total_earned = Column(Float, default=0.0)
    total_supported = Column(Float, default=0.0)
    
    # ✨ ポイントシステム
    free_points = Column(Float, default=0.0, comment="無料ポイント（新規登録特典など）")
    points_earned = Column(Float, default=0.0, comment="収益で獲得したポイント")
    points_used = Column(Float, default=0.0, comment="使用済みポイント")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 🔗 リレーション（修正）
    creators = relationship("Creator", back_populates="owner")  # ← "user" → "owner" に修正
    support_logs = relationship("SupportLog", back_populates="supporter")
    uploaded_files = relationship("UploadedFile", back_populates="uploader")

class Creator(Base):
    __tablename__ = "creators"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    image_url = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    
    # 推し活ビジネス向けフィールド
    category = Column(String, default="VTuber")
    
    # 🎯 新しい分配方式（プラットフォーム手数料15%固定）
    creator_fan_split = Column(Float, default=0.8)  # クリエイター：ファン = 80:20 で残り85%を分配
    
    # 自動計算される分配率（表示・計算用）
    revenue_share = Column(Float, default=0.68)      # 85% × 80% = 68%
    fan_commission_rate = Column(Float, default=0.17) # 85% × 20% = 17%
    platform_fee_rate = Column(Float, default=PLATFORM_FEE_RATE)  # 15%固定
    
    # 統計情報
    total_revenue = Column(Float, default=0.0)
    total_supporters = Column(Integer, default=0)
    monthly_revenue = Column(Float, default=0.0)
    
    # 設定
    is_active = Column(Boolean, default=True)
    allow_ai_content = Column(Boolean, default=True)
    
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 🔗 リレーション（修正）
    owner = relationship("User", back_populates="creators")  # ← 対応関係を統一
    support_logs = relationship("SupportLog", back_populates="creator")

class SupportLog(Base):
    __tablename__ = "support_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    creator_id = Column(Integer, ForeignKey("creators.id"))
    supporter_id = Column(Integer, ForeignKey("users.id"))
    
    # 推し活ビジネス向け拡張
    support_type = Column(String, default="direct")
    amount = Column(Float)
    
    # 分配詳細
    creator_share = Column(Float)
    fan_commission = Column(Float)
    platform_fee = Column(Float)
    
    # 追加情報
    message = Column(Text, nullable=True)
    
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # リレーション
    creator = relationship("Creator", back_populates="support_logs")
    supporter = relationship("User", back_populates="support_logs")

# ✨ 新規追加: ファイルアップロード用テーブル
class UploadedFile(Base):
    __tablename__ = "uploaded_files"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)  # 保存されたファイル名（一意）
    original_filename = Column(String, nullable=False)  # 元のファイル名
    file_path = Column(String, nullable=False)  # ファイルの保存パス
    file_size = Column(Integer, nullable=False)  # ファイルサイズ（バイト）
    content_type = Column(String, nullable=False)  # MIMEタイプ
    
    # ファイル分類・タグ
    file_category = Column(String, nullable=True)  # image, video, audio, document等
    tags = Column(String, nullable=True)  # ユーザー定義タグ（カンマ区切り）
    description = Column(Text, nullable=True)  # ファイルの説明
    
    # アクセス制御
    is_public = Column(Boolean, default=False)  # 公開ファイルかどうか
    is_ai_generated = Column(Boolean, default=False)  # AI生成コンテンツかどうか
    
    # 関連クリエイター（オプション）
    related_creator_id = Column(Integer, ForeignKey("creators.id"), nullable=True)
    
    # メタデータ
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    upload_date = Column(DateTime, default=datetime.utcnow)
    last_accessed = Column(DateTime, nullable=True)  # 最後にアクセスされた日時
    download_count = Column(Integer, default=0)  # ダウンロード回数
    
    # リレーション
    uploader = relationship("User", back_populates="uploaded_files")
    related_creator = relationship("Creator", foreign_keys=[related_creator_id])

# ✨ 新規追加: ファイル共有・コラボレーション用テーブル
class FileShare(Base):
    __tablename__ = "file_shares"
    
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("uploaded_files.id"), nullable=False)
    shared_with_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    shared_with_creator_id = Column(Integer, ForeignKey("creators.id"), nullable=True)
    
    # アクセス権限
    permission_level = Column(String, default="view")  # view, download, edit
    expires_at = Column(DateTime, nullable=True)  # 共有期限
    
    # シェア情報
    share_token = Column(String, unique=True, nullable=True)  # 公開リンク用トークン
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # リレーション
    file = relationship("UploadedFile")
    shared_with_user = relationship("User", foreign_keys=[shared_with_user_id])
    shared_with_creator = relationship("Creator", foreign_keys=[shared_with_creator_id])
    creator = relationship("User", foreign_keys=[created_by])

# ✨ 新規追加: AI生成コンテンツ管理用テーブル（将来のAI機能用）
class AIGeneratedContent(Base):
    __tablename__ = "ai_generated_contents"
    
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("uploaded_files.id"), nullable=False)
    creator_id = Column(Integer, ForeignKey("creators.id"), nullable=False)
    
    # AI生成情報
    ai_model_used = Column(String, nullable=True)  # 使用したAIモデル
    generation_prompt = Column(Text, nullable=True)  # 生成に使用したプロンプト
    generation_parameters = Column(Text, nullable=True)  # 生成パラメータ（JSON形式）
    
    # 収益情報
    estimated_revenue = Column(Float, default=0.0)  # 予想収益
    actual_revenue = Column(Float, default=0.0)  # 実際の収益
    
    # 承認状況
    creator_approved = Column(Boolean, default=False)  # クリエイターが承認したか
    is_published = Column(Boolean, default=False)  # 公開されているか
    
    # メタデータ
    generated_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    
    # リレーション
    file = relationship("UploadedFile")
    creator = relationship("Creator")
    generator = relationship("User")

# ✨ データベース初期化関数
def init_database():
    """データベースの初期化（テーブル作成）"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    DATABASE_URL = "sqlite:///./fan_platform.db"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    
    Base.metadata.create_all(bind=engine)
    print("✅ データベーステーブルが作成されました")
    return engine

# ✨ サンプルデータ作成関数
def create_sample_data():
    """開発・テスト用のサンプルデータを作成"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from auth import get_password_hash
    
    DATABASE_URL = "sqlite:///./fan_platform.db"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    db = SessionLocal()
    
    try:
        # サンプルユーザーがまだ存在しない場合のみ作成
        if not db.query(User).filter(User.username == "testuser").first():
            # テストユーザー作成
            test_user = User(
                username="testuser",
                email="test@example.com",
                hashed_password=get_password_hash("password123"),  # パスワードを統一
                free_points=1000.0  # 1000ポイントに変更
            )
            db.add(test_user)
            db.commit()
            db.refresh(test_user)
            
            # テストクリエイター作成
            test_creator = Creator(
                name="テスト推しクリエイター",
                description="ファイルアップロード機能をテストするためのクリエイター",
                category="VTuber",
                creator_fan_split=0.8,
                revenue_share=0.68,
                fan_commission_rate=0.17,
                platform_fee_rate=PLATFORM_FEE_RATE,
                user_id=test_user.id
            )
            db.add(test_creator)
            db.commit()
            
            print("✅ サンプルデータが作成されました")
            print(f"   ユーザー: testuser / パスワード: password123")
            print(f"   ポイント: 1000P")
            print(f"   クリエイター: {test_creator.name}")
        else:
            print("ℹ️ サンプルデータは既に存在します")
            
    except Exception as e:
        print(f"❌ サンプルデータ作成エラー: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    # 直接実行された場合はデータベース初期化とサンプルデータ作成
    print("🔧 データベースを初期化中...")
    init_database()
    create_sample_data()
    print("🎉 セットアップ完了！")