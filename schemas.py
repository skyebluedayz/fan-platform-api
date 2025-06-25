from pydantic import BaseModel, ConfigDict, Field
from typing import Optional

# --- クリエイターの作成・更新用スキーマ ---
class CreatorBase(BaseModel):
    name: str
    image_url: Optional[str] = None
    description: Optional[str] = None
    revenue_share: float = Field(0.5, ge=0.0, le=1.0)  # 0.0〜1.0の制限付き

# --- 登録時用（POST） ---
class CreatorCreate(CreatorBase):
    pass

# --- 応答用スキーマ（レスポンスにidやuser_idが含まれる） ---
class Creator(CreatorBase):
    id: int
    user_id: int

    # Pydantic v2 用の設定
    model_config = ConfigDict(from_attributes=True)

# --- 更新時用（PUT） ---
class CreatorUpdate(BaseModel):
    name: Optional[str] = None
    image_url: Optional[str] = None
    description: Optional[str] = None
    revenue_share: Optional[float] = Field(None, ge=0.0, le=1.0)
