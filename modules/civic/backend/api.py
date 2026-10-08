from fastapi import APIRouter
from app.schemas import CATEGORIES

router = APIRouter(prefix="/civic", tags=["Civic"])


@router.get("/categories")
def categories():
    return CATEGORIES
