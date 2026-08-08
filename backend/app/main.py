"""FastAPI 主入口模块"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import settings
from app.database import init_db, close_db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"[INFO] 启动 {settings.APP_NAME} v{settings.APP_VERSION}")
    await init_db()
    logger.info("[OK] 数据库初始化完成")
    yield
    await close_db()
    logger.info("[END] 应用关闭")


app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION, description="智能论文精读ai agent系统", lifespan=lifespan, redirect_slashes=False)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

from app.api.auth import router as auth_router
from app.api.papers import router as papers_router
from app.api.notes import router as notes_router
app.include_router(auth_router)
app.include_router(papers_router)
app.include_router(notes_router)


@app.get("/")
async def root():
    return {"name": settings.APP_NAME, "version": settings.APP_VERSION, "description": "智能论文精读ai agent系统"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}