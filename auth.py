# auth.py - 推し活ビジネス対応版

from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import SessionLocal
from models import User as DBUser  # 更新されたUserモデルを使用

# --- 設定 ---
SECRET_KEY = "your-secret-key-change-this-in-production"
ALGORITHM = "HS256"

# --- パスワードハッシュ化設定 ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- OAuth2設定 ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# --- データベース接続 ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- パスワード関連 ---
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """平文パスワードとハッシュ化パスワードを照合"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """パスワードをハッシュ化"""
    return pwd_context.hash(password)

# --- ユーザー認証 ---
def authenticate_user(db: Session, username: str, password: str) -> DBUser:
    """ユーザー認証"""
    user = db.query(DBUser).filter(DBUser.username == username).first()
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

# --- JWT トークン ---
def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """JWTアクセストークン作成"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> DBUser:
    """現在のユーザーを取得（JWT認証）"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(DBUser).filter(DBUser.username == username).first()
    if user is None:
        raise credentials_exception
    
    return user