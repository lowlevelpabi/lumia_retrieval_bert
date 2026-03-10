from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.api.deps import admin_required
from app.models.user import User
from app.schemas.user import UserResponse
from app.schemas.user import UserResponse, UserRoleUpdate

router = APIRouter()

@router.get("/", response_model=List[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    admin_user: User = Depends(admin_required)
):
    """
    Get all users. Only accessible by admins.
    """
    return db.query(User).all()

@router.patch("/{user_id}/role", response_model=UserResponse)
def change_user_role(
    user_id: int,
    body: UserRoleUpdate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(admin_required)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="User not found")
    user.role = body.role
    db.commit()
    db.refresh(user)
    return user