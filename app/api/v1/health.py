from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.api import deps

router = APIRouter()

@router.get("")
def health_check(db: Session = Depends(deps.get_db)):
    """Health check endpoint. Also verifies database connectivity."""
    try:
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = "unhealthy"
        # In a real app, you might want to return a 503 Service Unavailable here
        # or log the error. We'll return 200 but indicate db is unhealthy.
    
    return {
        "status": "ok",
        "database": db_status
    }
