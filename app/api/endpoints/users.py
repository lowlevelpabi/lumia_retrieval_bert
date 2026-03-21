from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.api.deps import admin_required, get_current_user
from app.models.user import User
from app.models.paper import Paper
from app.models.citation import UserCitation
from app.schemas.paper import PaperResponse
from app.schemas.user import UserResponse
from app.schemas.user import UserResponse, UserRoleUpdate

router = APIRouter()

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Get current logged-in user details.
    """
    return current_user

@router.get("/me/citations", response_model=List[PaperResponse])
def get_my_citations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a list of papers the current user has cited.
    """
    citations = db.query(Paper).join(UserCitation).filter(UserCitation.user_id == current_user.id).all()
    return citations

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