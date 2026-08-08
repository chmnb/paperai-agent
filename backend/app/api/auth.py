"""认证模块 — JWT 令牌管理与用户认证"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.config import settings
from app.models.user import User
from app.database import get_db, AsyncSession
from jose import jwt, JWTError
from datetime import datetime, timedelta
from sqlalchemy import select
import hashlib
import uuid
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/auth")


def hash_password(password: str) -> str:
    salt = settings.SECRET_KEY
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()


def verify_password(password: str, hash_value: str) -> bool:
    return hash_password(password) == hash_value


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str


def create_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": user_id, "exp": expire},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None


@router.post("/register")
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == data.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")
    user = User(
        username=data.username,
        email=data.email,
        password_hash=hash_password(data.password),
    )
    db.add(user)
    await db.commit()
    token = create_token(str(user.id))
    return {"access_token": token, "token_type": "bearer", "user": user.to_dict()}


@router.post("/login")
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(
            (User.username == data.username) | (User.email == data.username)
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            username=data.username,
            email=f"{data.username}@paperai.local",
            password_hash=hash_password(data.password),
        )
        db.add(user)
        await db.commit()
    elif not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="密码错误")

    token = create_token(str(user.id))
    return {"access_token": token, "token_type": "bearer", "user": user.to_dict()}
