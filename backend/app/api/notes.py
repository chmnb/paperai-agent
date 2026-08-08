"""笔记 API 模块 (骨架)"""
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/notes")


@router.get("/")
async def list_notes():
    return {"notes": [], "total": 0}


@router.post("/")
async def create_note(data: dict):
    return {"message": "笔记功能开发中", "note_id": "placeholder"}
