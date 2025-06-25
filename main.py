import logging
from fastapi import FastAPI, HTTPException, Depends, status, Path, Query, File, UploadFile, Form
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import SessionLocal, engine
from models import Base, User as DBUser, Creator as DBCreator, SupportLog as DBSupportLog, UploadedFile as DBUploadedFile, PLATFORM_FEE_RATE
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime, timedelta
from fastapi.openapi.utils import get_openapi
from typing import Optional, List
import os
import shutil
import uuid
from pathlib import Path as PathLib

# 認証ロジックを外部からインポート
from auth import create_access_token, get_current_user, authenticate_user, get_password_hash, get_db

# --- ロギング設定 ---
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="推し活 × AI収益分配プラットフォーム API", 
    version="2.3.0",
    description="ファンがAIを使って推しクリエイターの販促素材を作成し、収益を分配するプラットフォーム（プラットフォーム手数料15%固定・クリエイター名重複防止・ファイルアップロード完全統合）"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では適切なドメインに変更
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静的ファイル（HTML, CSS, JS）を配信
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- ファイルアップロード設定 ---
UPLOAD_DIR = "uploads"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".pdf", ".txt", ".doc", ".docx", ".mp4", ".mp3", ".wav"}

# アップロードディレクトリの作成
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- セキュリティ設定 ---
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# --- DB初期化 ---
Base.metadata.create_all(bind=engine)

# --- スキーマ定義 ---
class UserCreate(BaseModel):
    username: str
    password: str
    email: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class UserProfile(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    is_creator_verified: bool
    total_earned: float
    total_supported: float
    created_at: datetime
    # ポイント情報を追加
    free_points: float = 0.0
    points_earned: float = 0.0
    points_used: float = 0.0
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str

class CreatorCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="クリエイター名（プラットフォーム全体で一意）")
    image_url: Optional[str] = None
    description: Optional[str] = None
    category: str = Field(default="VTuber", description="VTuber, インディーズバンド, イラストレーター等")
    creator_fan_split: float = Field(
        default=0.8, 
        ge=0.0, 
        le=1.0, 
        description="クリエイター：ファンの分配比率（0.8 = クリエイター80%：ファン20%で残り85%を分配）"
    )
    allow_ai_content: bool = Field(default=True, description="AI生成コンテンツを許可するか")

class Creator(BaseModel):
    id: int
    name: str
    image_url: Optional[str] = None
    description: Optional[str] = None
    category: str
    creator_fan_split: float
    revenue_share: float
    fan_commission_rate: float
    platform_fee_rate: float
    total_revenue: float
    total_supporters: int
    monthly_revenue: float
    is_active: bool
    allow_ai_content: bool
    user_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class CreatorUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="クリエイター名（プラットフォーム全体で一意）")
    image_url: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    creator_fan_split: Optional[float] = Field(
        default=None, 
        ge=0.0, 
        le=1.0,
        description="クリエイター：ファンの分配比率"
    )
    allow_ai_content: Optional[bool] = None

class SupportRequest(BaseModel):
    creator_id: int
    amount: float = Field(..., gt=0, description="支援額（正の数）")
    support_type: str = Field(default="direct", description="direct, ai_content_sale, subscription")
    message: Optional[str] = Field(default=None, description="支援メッセージ")

class SupportLogResponse(BaseModel):
    id: int
    creator_id: int
    creator_name: str
    amount: float
    support_type: str
    creator_share: float
    fan_commission: float
    platform_fee: float
    message: Optional[str]
    timestamp: datetime

class RevenueStats(BaseModel):
    total_platform_revenue: float
    total_creator_revenue: float
    total_fan_commission: float
    active_creators: int
    active_fans: int
    total_transactions: int
    platform_fee_rate: float

# --- ✨ ファイルアップロード用スキーマ（データベース統合版） ---
class FileUploadRequest(BaseModel):
    description: Optional[str] = None
    tags: Optional[str] = None
    is_public: bool = False
    is_ai_generated: bool = False
    related_creator_id: Optional[int] = None

class UploadedFileResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    file_size: int
    content_type: str
    file_category: Optional[str]
    tags: Optional[str]
    description: Optional[str]
    is_public: bool
    is_ai_generated: bool
    related_creator_id: Optional[int]
    upload_date: datetime
    last_accessed: Optional[datetime]
    download_count: int
    file_url: str
    model_config = ConfigDict(from_attributes=True)

class FileListResponse(BaseModel):
    files: List[UploadedFileResponse]
    total_count: int
    total_size: int
    categories: dict

class FileUpdateRequest(BaseModel):
    description: Optional[str] = None
    tags: Optional[str] = None
    is_public: Optional[bool] = None
    related_creator_id: Optional[int] = None

# --- ヘルパー関数 ---
def calculate_revenue_splits(creator_fan_split: float):
    """収益分配率を計算（プラットフォーム手数料15%固定）"""
    available_for_split = 1.0 - PLATFORM_FEE_RATE  # 85%
    revenue_share = available_for_split * creator_fan_split
    fan_commission_rate = available_for_split * (1.0 - creator_fan_split)
    
    return {
        "revenue_share": revenue_share,
        "fan_commission_rate": fan_commission_rate,
        "platform_fee_rate": PLATFORM_FEE_RATE
    }

def check_creator_name_duplicate(db: Session, name: str, exclude_id: Optional[int] = None):
    """クリエイター名の重複チェック"""
    query = db.query(DBCreator).filter(DBCreator.name == name)
    if exclude_id:
        query = query.filter(DBCreator.id != exclude_id)
    return query.first()

def generate_unique_filename(original_filename: str) -> str:
    """一意のファイル名を生成"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    file_ext = PathLib(original_filename).suffix
    return f"{timestamp}_{unique_id}_{original_filename}"

def validate_file(file: UploadFile) -> dict:
    """ファイルのバリデーション"""
    # ファイルサイズチェック
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400, 
            detail=f"ファイル '{file.filename}' が大きすぎます（最大: {MAX_FILE_SIZE//1024//1024}MB）"
        )
    
    # ファイル拡張子チェック
    file_ext = PathLib(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"ファイル形式 '{file_ext}' は許可されていません。許可形式: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    return {
        "original_filename": file.filename,
        "content_type": file.content_type,
        "file_extension": file_ext
    }

def get_file_category(file_extension: str) -> str:
    """ファイル拡張子からカテゴリを判定"""
    extension = file_extension.lower()
    if extension in {".jpg", ".jpeg", ".png", ".gif"}:
        return "image"
    elif extension in {".mp4", ".mov", ".avi"}:
        return "video"
    elif extension in {".mp3", ".wav", ".flac"}:
        return "audio"
    elif extension in {".pdf", ".doc", ".docx", ".txt"}:
        return "document"
    else:
        return "other"

# ホームページ・ダッシュボードを配信
@app.get("/", response_class=FileResponse)
def serve_homepage():
    """ホームページ（index.html）を配信"""
    return FileResponse('static/index.html')

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page():
    """統合ダッシュボードページ"""
    try:
        with open("templates/dashboard.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        # templates/dashboard.htmlが存在しない場合の仮ページ
        html_content = """
        <!DOCTYPE html>
        <html>
        <head><title>推し活プラットフォーム - ダッシュボード</title></head>
        <body>
            <h1>🎭 推し活プラットフォーム - ダッシュボード</h1>
            <p>統合ダッシュボードは準備中です。</p>
            <p><a href="/docs">API仕様書はこちら</a></p>
            <div>
                <h2>📁 ファイル管理機能テスト</h2>
                <p>✅ ファイルアップロード: <code>POST /api/upload</code></p>
                <p>✅ ファイル一覧: <code>GET /api/files</code></p>
                <p>✅ ファイル削除: <code>DELETE /api/files/{file_id}</code></p>
                <p>✅ ファイル配信: <code>GET /uploads/{filename}</code></p>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)

# --- ユーザー登録・ログイン ---
@app.post("/register", tags=["認証"])
def register(user: UserCreate, db: Session = Depends(get_db)):
    """ユーザー登録（1000ポイント自動付与）"""
    if db.query(DBUser).filter(DBUser.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already registered")
    
    if user.email and db.query(DBUser).filter(DBUser.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_pw = get_password_hash(user.password)
    new_user = DBUser(
        username=user.username, 
        hashed_password=hashed_pw,
        email=user.email,
        free_points=1000.0  # 新規登録時1000ポイント付与
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    logger.info(f"User registered successfully: {user.username} with 1000 free points")
    return {
        "message": "User registered successfully", 
        "welcome_bonus": "🎁 1000ポイントを付与しました！"
    }

@app.post("/login", response_model=Token, tags=["認証"])
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """ユーザーログイン（OAuth2PasswordRequestForm）"""
    try:
        user = authenticate_user(db, form_data.username, form_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username}, 
            expires_delta=access_token_expires
        )
        
        logger.info(f"User logged in successfully: {user.username}")
        return {"access_token": access_token, "token_type": "bearer"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login"
        )

@app.post("/auth/login", response_model=Token, tags=["認証"])
def login_json(user_login: UserLogin, db: Session = Depends(get_db)):
    """ユーザーログイン（JSON形式）"""
    try:
        user = authenticate_user(db, user_login.username, user_login.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username}, 
            expires_delta=access_token_expires
        )
        
        logger.info(f"User logged in successfully (JSON): {user.username}")
        return {"access_token": access_token, "token_type": "bearer"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during JSON login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login"
        )

# --- ユーザープロフィール ---
@app.get("/profile", response_model=UserProfile, tags=["ユーザー管理"])
async def get_user_profile(current_user: DBUser = Depends(get_current_user)):
    """ユーザープロフィール取得"""
    return current_user

# ポイント残高確認
@app.get("/profile/points", tags=["ユーザー管理"])
async def get_points_balance(current_user: DBUser = Depends(get_current_user)):
    """ポイント残高確認"""
    return {
        "username": current_user.username,
        "balances": {
            "💳 使用可能ポイント": current_user.free_points,
            "💰 獲得ポイント": current_user.points_earned,
            "📊 使用済みポイント": current_user.points_used
        }
    }

# --- ✨ ファイルアップロード機能（完全データベース統合版） ---
@app.post("/api/upload", response_model=List[UploadedFileResponse], tags=["📁 ファイル管理"])
async def upload_files(
    files: List[UploadFile] = File(...),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    is_public: bool = Form(False),
    is_ai_generated: bool = Form(False),
    related_creator_id: Optional[int] = Form(None),
    current_user: DBUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """複数ファイルのアップロード（データベース統合版）"""
    uploaded_files = []
    
    # 関連クリエイターの検証
    if related_creator_id:
        creator = db.query(DBCreator).filter(DBCreator.id == related_creator_id).first()
        if not creator:
            raise HTTPException(status_code=404, detail="指定されたクリエイターが見つかりません")
        if creator.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="指定されたクリエイターにアクセス権限がありません")
    
    for file in files:
        try:
            # ファイル検証
            file_info = validate_file(file)
            
            # 一意のファイル名生成
            unique_filename = generate_unique_filename(file.filename)
            file_path = os.path.join(UPLOAD_DIR, unique_filename)
            
            # ファイル保存
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # ファイルサイズを取得
            file_size = os.path.getsize(file_path)
            
            # ファイルカテゴリを判定
            file_category = get_file_category(PathLib(file.filename).suffix)
            
            # ✨ データベースに記録
            db_file = DBUploadedFile(
                filename=unique_filename,
                original_filename=file.filename,
                file_path=file_path,
                file_size=file_size,
                content_type=file.content_type or "application/octet-stream",
                file_category=file_category,
                tags=tags,
                description=description,
                is_public=is_public,
                is_ai_generated=is_ai_generated,
                related_creator_id=related_creator_id,
                uploaded_by=current_user.id
            )
            
            db.add(db_file)
            db.commit()
            db.refresh(db_file)
            
            # レスポンス用データ作成
            file_response = UploadedFileResponse(
                id=db_file.id,
                filename=db_file.filename,
                original_filename=db_file.original_filename,
                file_size=db_file.file_size,
                content_type=db_file.content_type,
                file_category=db_file.file_category,
                tags=db_file.tags,
                description=db_file.description,
                is_public=db_file.is_public,
                is_ai_generated=db_file.is_ai_generated,
                related_creator_id=db_file.related_creator_id,
                upload_date=db_file.upload_date,
                last_accessed=db_file.last_accessed,
                download_count=db_file.download_count,
                file_url=f"/uploads/{db_file.filename}"
            )
            
            uploaded_files.append(file_response)
            
            logger.info(f"File uploaded: {file.filename} -> {unique_filename} by user {current_user.username} (ID: {db_file.id})")
            
        except Exception as e:
            logger.error(f"File upload error for {file.filename}: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail=f"ファイル '{file.filename}' のアップロードに失敗しました: {str(e)}"
            )
    
    return uploaded_files

@app.get("/api/files", response_model=FileListResponse, tags=["📁 ファイル管理"])
async def get_user_files(
    category: Optional[str] = Query(None, description="ファイルカテゴリでフィルタ"),
    is_public: Optional[bool] = Query(None, description="公開ファイルのみ表示"),
    creator_id: Optional[int] = Query(None, description="特定クリエイターのファイルのみ"),
    limit: int = Query(50, le=100),
    current_user: DBUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """ユーザーのアップロードファイル一覧（データベース統合版）"""
    
    # ベースクエリ
    query = db.query(DBUploadedFile).filter(DBUploadedFile.uploaded_by == current_user.id)
    
    # フィルタ適用
    if category:
        query = query.filter(DBUploadedFile.file_category == category)
    if is_public is not None:
        query = query.filter(DBUploadedFile.is_public == is_public)
    if creator_id:
        query = query.filter(DBUploadedFile.related_creator_id == creator_id)
    
    # ファイル取得
    files = query.order_by(DBUploadedFile.upload_date.desc()).limit(limit).all()
    
    # 統計計算
    total_size = sum(f.file_size for f in files)
    
    # カテゴリ別統計
    categories = {}
    all_files = db.query(DBUploadedFile).filter(DBUploadedFile.uploaded_by == current_user.id).all()
    for file in all_files:
        cat = file.file_category or "other"
        if cat not in categories:
            categories[cat] = {"count": 0, "size": 0}
        categories[cat]["count"] += 1
        categories[cat]["size"] += file.file_size
    
    # レスポンスデータ作成
    file_responses = []
    for file in files:
        file_responses.append(UploadedFileResponse(
            id=file.id,
            filename=file.filename,
            original_filename=file.original_filename,
            file_size=file.file_size,
            content_type=file.content_type,
            file_category=file.file_category,
            tags=file.tags,
            description=file.description,
            is_public=file.is_public,
            is_ai_generated=file.is_ai_generated,
            related_creator_id=file.related_creator_id,
            upload_date=file.upload_date,
            last_accessed=file.last_accessed,
            download_count=file.download_count,
            file_url=f"/uploads/{file.filename}"
        ))
    
    return FileListResponse(
        files=file_responses,
        total_count=len(file_responses),
        total_size=total_size,
        categories=categories
    )

@app.get("/api/files/{file_id}", response_model=UploadedFileResponse, tags=["📁 ファイル管理"])
async def get_file_details(
    file_id: int,
    current_user: DBUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """ファイル詳細取得"""
    file_record = db.query(DBUploadedFile).filter(
        DBUploadedFile.id == file_id,
        DBUploadedFile.uploaded_by == current_user.id
    ).first()
    
    if not file_record:
        raise HTTPException(status_code=404, detail="ファイルが見つかりません")
    
    # アクセス日時更新
    file_record.last_accessed = datetime.utcnow()
    db.commit()
    
    return UploadedFileResponse(
        id=file_record.id,
        filename=file_record.filename,
        original_filename=file_record.original_filename,
        file_size=file_record.file_size,
        content_type=file_record.content_type,
        file_category=file_record.file_category,
        tags=file_record.tags,
        description=file_record.description,
        is_public=file_record.is_public,
        is_ai_generated=file_record.is_ai_generated,
        related_creator_id=file_record.related_creator_id,
        upload_date=file_record.upload_date,
        last_accessed=file_record.last_accessed,
        download_count=file_record.download_count,
        file_url=f"/uploads/{file_record.filename}"
    )

@app.put("/api/files/{file_id}", response_model=UploadedFileResponse, tags=["📁 ファイル管理"])
async def update_file_metadata(
    file_id: int,
    update_data: FileUpdateRequest,
    current_user: DBUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """ファイルメタデータ更新"""
    file_record = db.query(DBUploadedFile).filter(
        DBUploadedFile.id == file_id,
        DBUploadedFile.uploaded_by == current_user.id
    ).first()
    
    if not file_record:
        raise HTTPException(status_code=404, detail="ファイルが見つかりません")
    
    # 関連クリエイターの検証
    if update_data.related_creator_id:
        creator = db.query(DBCreator).filter(DBCreator.id == update_data.related_creator_id).first()
        if not creator:
            raise HTTPException(status_code=404, detail="指定されたクリエイターが見つかりません")
        if creator.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="指定されたクリエイターにアクセス権限がありません")
    
    # 更新データ適用
    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(file_record, key, value)
    
    db.commit()
    db.refresh(file_record)
    
    logger.info(f"File metadata updated: {file_record.filename} by user {current_user.username}")
    
    return UploadedFileResponse(
        id=file_record.id,
        filename=file_record.filename,
        original_filename=file_record.original_filename,
        file_size=file_record.file_size,
        content_type=file_record.content_type,
        file_category=file_record.file_category,
        tags=file_record.tags,
        description=file_record.description,
        is_public=file_record.is_public,
        is_ai_generated=file_record.is_ai_generated,
        related_creator_id=file_record.related_creator_id,
        upload_date=file_record.upload_date,
        last_accessed=file_record.last_accessed,
        download_count=file_record.download_count,
        file_url=f"/uploads/{file_record.filename}"
    )

@app.delete("/api/files/{file_id}", tags=["📁 ファイル管理"])
async def delete_file(
    file_id: int,
    current_user: DBUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """ファイル削除（データベース統合版）"""
    file_record = db.query(DBUploadedFile).filter(
        DBUploadedFile.id == file_id,
        DBUploadedFile.uploaded_by == current_user.id
    ).first()
    
    if not file_record:
        raise HTTPException(status_code=404, detail="ファイルが見つかりません")
    
    try:
        # 物理ファイル削除
        if os.path.exists(file_record.file_path):
            os.remove(file_record.file_path)
        
        # データベースから削除
        db.delete(file_record)
        db.commit()
        
        logger.info(f"File deleted: {file_record.filename} (ID: {file_id}) by user {current_user.username}")
        return {"success": True, "message": f"ファイル '{file_record.original_filename}' を削除しました"}
        
    except Exception as e:
        logger.error(f"File deletion error: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="ファイル削除に失敗しました")

# アップロードされたファイルの配信
@app.get("/uploads/{filename}")
async def serve_uploaded_file(
    filename: str,
    db: Session = Depends(get_db)
):
    """アップロードされたファイルを配信（ダウンロード数カウント付き）"""
    # ファイル存在確認
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="ファイルが見つかりません")
    
    # ダウンロード数更新
    file_record = db.query(DBUploadedFile).filter(DBUploadedFile.filename == filename).first()
    if file_record:
        file_record.download_count += 1
        file_record.last_accessed = datetime.utcnow()
        db.commit()
    
    return FileResponse(file_path)

# --- API専用エンドポイント ---
@app.get("/api/home")
def api_root():
    """API専用ホームエンドポイント"""
    return {
        "message": "🌟 推し活 × AI収益分配プラットフォーム API へようこそ！",
        "features": [
            "💡 ファンがAIで推しの販促素材を作成",
            "💰 収益をクリエイターとファンで分配", 
            "🚀 推し活しながら収益化が可能",
            "🛡️ クリエイター名重複防止でブランド保護",
            "📁 完全統合されたファイル管理システム"
        ],
        "platform_info": {
            "platform_fee": f"{PLATFORM_FEE_RATE*100:.0f}%固定",
            "user_configurable": "クリエイター：ファンの分配比率のみ",
            "duplicate_prevention": "クリエイター名はプラットフォーム全体で一意",
            "file_upload": f"最大{MAX_FILE_SIZE//1024//1024}MB、対応形式: {', '.join(ALLOWED_EXTENSIONS)}",
            "database_integration": "ファイル管理完全データベース統合済み"
        },
        "status": "Ready for MVP testing! 🎉"
    }

@app.get("/protected", tags=["認証"])
async def protected_route(current_user: DBUser = Depends(get_current_user)):
    """保護されたエンドポイント"""
    return {
        "message": f"Hello, {current_user.username}! 推し活プラットフォームへようこそ！",
        "user_id": current_user.id,
        "total_earned": current_user.total_earned,
        "total_supported": current_user.total_supported,
        "free_points": current_user.free_points
    }

# --- 推しクリエイター管理 ---
@app.post("/creators/", response_model=Creator, tags=["📱 推しクリエイター管理"])
async def create_creator(
    creator: CreatorCreate, 
    db: Session = Depends(get_db), 
    current_user: DBUser = Depends(get_current_user)
):
    """推しクリエイター登録（プラットフォーム手数料15%固定・重複防止機能付き）"""
    
    # クリエイター名の重複チェック（グローバル）
    existing_creator = check_creator_name_duplicate(db, creator.name)
    if existing_creator:
        logger.warning(f"Creator name duplicate attempt: '{creator.name}' by user {current_user.username}")
        raise HTTPException(
            status_code=400,
            detail=f"❌ クリエイター名「{creator.name}」は既に登録されています。別の名前をお選びください。"
        )
    
    # 収益分配率を計算
    splits = calculate_revenue_splits(creator.creator_fan_split)
    
    db_creator = DBCreator(
        name=creator.name,
        image_url=creator.image_url,
        description=creator.description,
        category=creator.category,
        creator_fan_split=creator.creator_fan_split,
        revenue_share=splits["revenue_share"],
        fan_commission_rate=splits["fan_commission_rate"],
        platform_fee_rate=splits["platform_fee_rate"],
        allow_ai_content=creator.allow_ai_content,
        user_id=current_user.id
    )
    db.add(db_creator)
    db.commit()
    db.refresh(db_creator)
    
    logger.info(f"Creator created: '{creator.name}' by user {current_user.username} with split {creator.creator_fan_split}")
    return db_creator

@app.get("/creators/", response_model=List[Creator], tags=["📱 推しクリエイター管理"])
async def read_my_creators(
    db: Session = Depends(get_db), 
    current_user: DBUser = Depends(get_current_user)
):
    """自分が登録した推しクリエイター一覧"""
    return db.query(DBCreator).filter(DBCreator.user_id == current_user.id).all()

@app.get("/creators/public", response_model=List[Creator], tags=["📱 推しクリエイター管理"])
async def read_public_creators(
    category: Optional[str] = Query(None, description="カテゴリでフィルタ"),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db)
):
    """🌟 公開中の全推しクリエイター一覧（支援対象）"""
    query = db.query(DBCreator).filter(DBCreator.is_active == True)
    
    if category:
        query = query.filter(DBCreator.category == category)
    
    creators = query.limit(limit).all()
    logger.info(f"Public creators fetched: {len(creators)} creators")
    return creators

@app.put("/creators/{creator_id}", response_model=Creator, tags=["📱 推しクリエイター管理"])
async def update_creator(
    creator_update: CreatorUpdate, 
    creator_id: int = Path(...), 
    current_user: DBUser = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """推しクリエイター情報更新（重複防止機能付き）"""
    creator = db.query(DBCreator).filter(DBCreator.id == creator_id).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")
    if creator.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    update_data = creator_update.model_dump(exclude_unset=True)
    
    # クリエイター名の重複チェック（更新時）
    if 'name' in update_data:
        existing_creator = check_creator_name_duplicate(db, update_data['name'], exclude_id=creator_id)
        if existing_creator:
            logger.warning(f"Creator name duplicate attempt during update: '{update_data['name']}' by user {current_user.username}")
            raise HTTPException(
                status_code=400,
                detail=f"❌ クリエイター名「{update_data['name']}」は既に使用されています。別の名前をお選びください。"
            )
    
    # creator_fan_split が更新された場合、分配率を再計算
    if 'creator_fan_split' in update_data:
        splits = calculate_revenue_splits(update_data['creator_fan_split'])
        update_data.update(splits)
    
    for key, value in update_data.items():
        setattr(creator, key, value)
    
    db.commit()
    db.refresh(creator)
    
    logger.info(f"Creator updated: '{creator.name}' by user {current_user.username}")
    return creator

# --- 推し活支援機能（収益分配付き）---
@app.post("/support", tags=["💰 推し活支援"])
async def support_creator(
    support: SupportRequest, 
    current_user: DBUser = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """💝 推しクリエイター支援（プラットフォーム手数料15%固定）"""
    # クリエイター存在確認
    creator = db.query(DBCreator).filter(DBCreator.id == support.creator_id).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")
    
    # アクティブ状態確認
    if not creator.is_active:
        raise HTTPException(status_code=400, detail="Creator is not active")
    
    # 自己支援チェック（強化版）
    if creator.user_id == current_user.id:
        logger.warning(f"Self-support attempt: User {current_user.id} tried to support own creator {creator.id}")
        raise HTTPException(
            status_code=400, 
            detail=f"❌ 自分が登録したクリエイター「{creator.name}」には支援できません"
        )
    
    # 支援額の妥当性チェック
    if support.amount <= 0:
        raise HTTPException(status_code=400, detail="支援額は正の数である必要があります")
    
    # 収益分配計算（プラットフォーム手数料15%固定）
    creator_share = support.amount * creator.revenue_share
    fan_commission = support.amount * creator.fan_commission_rate
    platform_fee = support.amount * PLATFORM_FEE_RATE
    
    # 分配合計の検証
    total_check = creator_share + fan_commission + platform_fee
    if abs(total_check - support.amount) > 0.01:  # 0.01円の誤差許容
        logger.error(f"Revenue split calculation error: {total_check} != {support.amount}")
        raise HTTPException(status_code=500, detail="収益分配計算エラー")
    
    # 支援ログ作成
    support_log = DBSupportLog(
        creator_id=support.creator_id,
        supporter_id=current_user.id,
        support_type=support.support_type,
        amount=support.amount,
        creator_share=creator_share,
        fan_commission=fan_commission,
        platform_fee=platform_fee,
        message=support.message
    )
    db.add(support_log)
    
    # 統計更新
    creator.total_revenue += creator_share
    creator.total_supporters = db.query(DBSupportLog).filter(
        DBSupportLog.creator_id == creator.id
    ).distinct(DBSupportLog.supporter_id).count() + 1
    
    # ユーザー統計更新
    current_user.total_supported += support.amount
    current_user.total_earned += fan_commission
    
    db.commit()
    db.refresh(support_log)
    
    logger.info(f"Support completed: {support.amount}円 from user {current_user.id} to creator {creator.name}")
    
    return {
        "message": f"🎉 '{creator.name}'への支援が完了しました！",
        "support_id": support_log.id,
        "breakdown": {
            "💸 支援総額": f"{support.amount:,.0f}円",
            "🎭 クリエイター受取": f"{creator_share:,.0f}円 ({creator.revenue_share*100:.1f}%)",
            "💰 あなたの還元": f"{fan_commission:,.0f}円 ({creator.fan_commission_rate*100:.1f}%)",
            "🏢 プラットフォーム手数料": f"{platform_fee:,.0f}円 ({PLATFORM_FEE_RATE*100:.0f}%固定)"
        },
        "split_info": f"クリエイター：ファン = {creator.creator_fan_split*100:.0f}%:{(1-creator.creator_fan_split)*100:.0f}%",
        "timestamp": support_log.timestamp,
    }

@app.post("/support/points", tags=["💰 推し活支援"])
async def support_with_points(
    support: SupportRequest,
    current_user: DBUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """ポイントでの支援（テスト用）"""
    
    # ポイント残高チェック
    if current_user.free_points < support.amount:
        raise HTTPException(
            status_code=400,
            detail=f"❌ ポイント不足です。残高: {current_user.free_points}P, 必要: {support.amount}P"
        )
    
    # クリエイター存在確認
    creator = db.query(DBCreator).filter(DBCreator.id == support.creator_id).first()
    if not creator:
        raise HTTPException(status_code=404, detail="クリエイターが見つかりません")
    
    # 自己支援チェック
    if creator.user_id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="❌ 自分のクリエイターには支援できません"
        )
    
    # 収益分配計算
    creator_share = support.amount * creator.revenue_share
    fan_commission = support.amount * creator.fan_commission_rate
    platform_fee = support.amount * PLATFORM_FEE_RATE
    
    # ポイント移動
    current_user.free_points -= support.amount
    current_user.points_used += support.amount
    current_user.points_earned += fan_commission
    
    # クリエイター統計更新
    creator.total_revenue += creator_share
    creator.total_supporters = db.query(DBSupportLog).filter(
        DBSupportLog.creator_id == creator.id
    ).distinct(DBSupportLog.supporter_id).count() + 1
    
    # クリエイターユーザーの収益更新
    creator_user = db.query(DBUser).filter(DBUser.id == creator.user_id).first()
    if creator_user:
        creator_user.points_earned += creator_share
    
    # 支援ログ作成
    support_log = DBSupportLog(
        creator_id=support.creator_id,
        supporter_id=current_user.id,
        support_type="points_test",
        amount=support.amount,
        creator_share=creator_share,
        fan_commission=fan_commission,
        platform_fee=platform_fee,
        message=f"🧪 ポイントテスト: {support.message or ''}"
    )
    db.add(support_log)
    
    db.commit()
    
    return {
        "message": f"🎉 ポイントで'{creator.name}'を支援しました！",
        "support_id": support_log.id,
        "breakdown": {
            "💸 使用ポイント": f"{support.amount}P",
            "🎭 クリエイター受取": f"{creator_share:.1f}P",
            "💰 あなたの還元": f"{fan_commission:.1f}P",
            "🏢 プラットフォーム手数料": f"{platform_fee:.1f}P"
        },
        "your_balance": {
            "💳 残りポイント": f"{current_user.free_points:.1f}P",
            "💰 獲得ポイント合計": f"{current_user.points_earned:.1f}P"
        }
    }

@app.get("/support/history", response_model=List[SupportLogResponse], tags=["💰 推し活支援"])
async def get_support_history(
    current_user: DBUser = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """📊 支援履歴取得"""
    logs = (db.query(DBSupportLog)
            .join(DBCreator)
            .filter(DBSupportLog.supporter_id == current_user.id)
            .order_by(DBSupportLog.timestamp.desc())
            .all())
    
    return [
        SupportLogResponse(
            id=log.id,
            creator_id=log.creator.id,
            creator_name=log.creator.name,
            amount=log.amount,
            support_type=log.support_type,
            creator_share=log.creator_share,
            fan_commission=log.fan_commission,
            platform_fee=log.platform_fee,
            message=log.message,
            timestamp=log.timestamp,
        ) for log in logs
    ]

# テスト用ポイント追加
@app.post("/test/add-points", tags=["🧪 テスト用"])
async def add_test_points(
    amount: float,
    current_user: DBUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """テスト用: ユーザーにポイントを追加"""
    current_user.free_points += amount
    db.commit()
    
    return {
        "message": f"🎁 {amount}ポイントを追加しました！",
        "new_balance": current_user.free_points
    }

# --- 収益統計 ---
@app.get("/stats", response_model=RevenueStats, tags=["📊 統計"])
async def get_platform_stats(
    current_user: DBUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """📈 プラットフォーム収益統計（プラットフォーム手数料15%固定）"""
    # 基本統計計算
    total_supports = db.query(DBSupportLog).all()
    
    total_platform_revenue = sum(log.platform_fee for log in total_supports)
    total_creator_revenue = sum(log.creator_share for log in total_supports)
    total_fan_commission = sum(log.fan_commission for log in total_supports)
    
    active_creators = db.query(DBCreator).filter(DBCreator.is_active == True).count()
    active_fans = db.query(DBUser).filter(DBUser.total_supported > 0).count()
    total_transactions = len(total_supports)
    
    return RevenueStats(
        total_platform_revenue=total_platform_revenue,
        total_creator_revenue=total_creator_revenue,
        total_fan_commission=total_fan_commission,
        active_creators=active_creators,
        active_fans=active_fans,
        total_transactions=total_transactions,
        platform_fee_rate=PLATFORM_FEE_RATE
    )

# --- プラットフォーム情報 ---
@app.get("/platform/info", tags=["📊 統計"])
async def get_platform_info():
    """プラットフォーム情報取得"""
    return {
        "platform_name": "推し活 × AI収益分配プラットフォーム",
        "version": "2.3.0",
        "platform_fee_rate": PLATFORM_FEE_RATE,
        "platform_fee_percentage": f"{PLATFORM_FEE_RATE*100:.0f}%",
        "revenue_model": "プラットフォーム手数料固定15% + ユーザー設定可能な分配比率",
        "security_features": [
            "クリエイター名重複防止（グローバル一意制約）",
            "自己支援防止機能",
            "収益分配計算検証",
            "ファイルアップロード完全統合セキュリティ"
        ],
        "file_upload_info": {
            "max_file_size": f"{MAX_FILE_SIZE//1024//1024}MB",
            "allowed_extensions": list(ALLOWED_EXTENSIONS),
            "upload_directory": UPLOAD_DIR,
            "database_integration": True,
            "features": [
                "メタデータ管理（タグ、説明、カテゴリ）",
                "アクセス制御（公開/非公開）",
                "クリエイター関連付け",
                "ダウンロード統計",
                "AI生成コンテンツ識別"
            ]
        },
        "example_splits": [
            {
                "creator_fan_split": 0.8,
                "result": "クリエイター68%：ファン17%：プラットフォーム15%"
            },
            {
                "creator_fan_split": 0.7,
                "result": "クリエイター59.5%：ファン25.5%：プラットフォーム15%"
            }
        ]
    }

# --- クリエイター名可用性チェック ---
@app.get("/creators/check-name/{creator_name}", tags=["📱 推しクリエイター管理"])
async def check_creator_name_availability(
    creator_name: str = Path(..., description="チェックしたいクリエイター名"),
    db: Session = Depends(get_db)
):
    """🔍 クリエイター名の使用可能性をチェック"""
    existing = check_creator_name_duplicate(db, creator_name)
    
    return {
        "name": creator_name,
        "available": existing is None,
        "message": f"✅ クリエイター名「{creator_name}」は使用可能です" if existing is None 
                  else f"❌ クリエイター名「{creator_name}」は既に使用されています",
        "suggestion": None if existing is None 
                     else f"「{creator_name} Official」や「{creator_name} 公式」などをお試しください"
    }

# --- ✨ 公開ファイル閲覧機能 ---
@app.get("/api/files/public", response_model=FileListResponse, tags=["📁 ファイル管理"])
async def get_public_files(
    category: Optional[str] = Query(None, description="ファイルカテゴリでフィルタ"),
    creator_id: Optional[int] = Query(None, description="特定クリエイターのファイルのみ"),
    limit: int = Query(50, le=100),
    db: Session = Depends(get_db)
):
    """公開ファイル一覧（認証不要）"""
    
    # ベースクエリ（公開ファイルのみ）
    query = db.query(DBUploadedFile).filter(DBUploadedFile.is_public == True)
    
    # フィルタ適用
    if category:
        query = query.filter(DBUploadedFile.file_category == category)
    if creator_id:
        query = query.filter(DBUploadedFile.related_creator_id == creator_id)
    
    # ファイル取得
    files = query.order_by(DBUploadedFile.upload_date.desc()).limit(limit).all()
    
    # 統計計算
    total_size = sum(f.file_size for f in files)
    
    # カテゴリ別統計
    categories = {}
    all_public_files = db.query(DBUploadedFile).filter(DBUploadedFile.is_public == True).all()
    for file in all_public_files:
        cat = file.file_category or "other"
        if cat not in categories:
            categories[cat] = {"count": 0, "size": 0}
        categories[cat]["count"] += 1
        categories[cat]["size"] += file.file_size
    
    # レスポンスデータ作成
    file_responses = []
    for file in files:
        file_responses.append(UploadedFileResponse(
            id=file.id,
            filename=file.filename,
            original_filename=file.original_filename,
            file_size=file.file_size,
            content_type=file.content_type,
            file_category=file.file_category,
            tags=file.tags,
            description=file.description,
            is_public=file.is_public,
            is_ai_generated=file.is_ai_generated,
            related_creator_id=file.related_creator_id,
            upload_date=file.upload_date,
            last_accessed=file.last_accessed,
            download_count=file.download_count,
            file_url=f"/uploads/{file.filename}"
        ))
    
    return FileListResponse(
        files=file_responses,
        total_count=len(file_responses),
        total_size=total_size,
        categories=categories
    )

# --- ファイル統計情報 ---
@app.get("/api/files/stats", tags=["📁 ファイル管理"])
async def get_file_stats(
    current_user: DBUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """ユーザーのファイル統計情報"""
    
    user_files = db.query(DBUploadedFile).filter(DBUploadedFile.uploaded_by == current_user.id).all()
    
    total_files = len(user_files)
    total_size = sum(f.file_size for f in user_files)
    total_downloads = sum(f.download_count for f in user_files)
    
    # カテゴリ別統計
    categories = {}
    for file in user_files:
        cat = file.file_category or "other"
        if cat not in categories:
            categories[cat] = {"count": 0, "size": 0, "downloads": 0}
        categories[cat]["count"] += 1
        categories[cat]["size"] += file.file_size
        categories[cat]["downloads"] += file.download_count
    
    # 公開ファイル数
    public_files = sum(1 for f in user_files if f.is_public)
    ai_generated_files = sum(1 for f in user_files if f.is_ai_generated)
    
    return {
        "user": current_user.username,
        "summary": {
            "total_files": total_files,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "total_downloads": total_downloads,
            "public_files": public_files,
            "ai_generated_files": ai_generated_files
        },
        "categories": categories,
        "storage_info": {
            "used_storage_mb": round(total_size / 1024 / 1024, 2),
            "max_file_size_mb": MAX_FILE_SIZE // 1024 // 1024,
            "allowed_extensions": list(ALLOWED_EXTENSIONS)
        }
    }

# --- テスト用DBリセット ---
if os.getenv("ENV") == "test":
    @app.post("/reset-db", tags=["🔧 テスト用"])
    def reset_database(db: Session = Depends(get_db)):
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        return {"message": "🔄 Database reset successful"}

# --- Swagger UIカスタム ---
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="推し活 × AI収益分配プラットフォーム API",
        version="2.3.0",
        description="ファンがAIを使って推しクリエイターの販促素材を作成し、収益を分配するプラットフォーム（プラットフォーム手数料15%固定・クリエイター名重複防止・ファイルアップロード完全統合）",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    
    # 保護されたエンドポイントにセキュリティを適用
    for path, path_item in openapi_schema["paths"].items():
        for method, operation in path_item.items():
            if method in ["get", "post", "put", "patch", "delete"]:
                if path not in ["/login", "/register", "/", "/creators/public", "/platform/info", "/creators/check-name/{creator_name}", "/uploads/{filename}", "/api/files/public", "/auth/login"]:
                    operation["security"] = [{"bearerAuth": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# --- サーバー起動（開発用） ---
if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 推し活プラットフォーム API サーバーを起動中...")
    logger.info(f"📁 アップロードディレクトリ: {UPLOAD_DIR}")
    logger.info(f"📏 最大ファイルサイズ: {MAX_FILE_SIZE//1024//1024}MB")
    logger.info(f"📋 許可ファイル形式: {', '.join(ALLOWED_EXTENSIONS)}")
    logger.info("✨ ファイルアップロード機能：完全データベース統合済み")
    logger.info("🔐 CORS設定：開発環境用（本番環境では要調整）")
    logger.info("🌐 JSON形式ログイン対応済み")
    # 文字列形式でアプリケーションを指定してreload機能を有効化
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)