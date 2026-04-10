from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from app.core.database import get_db
from app.core.security import get_password_hash, verify_password, create_access_token
from app.models.user import Student
from app.models.authorized_user import AuthorizedUser
from app.schemas.user import UserCreate, UserResponse, Token
from app.core.config import settings

router = APIRouter()

@router.post("/register", response_model=UserResponse)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    # Check if user exists in either table
    user = db.query(AuthorizedUser).filter(AuthorizedUser.username == user_in.username).first()
    if not user:
        user = db.query(Student).filter(Student.username == user_in.username).first()
    if user:
        raise HTTPException(status_code=400, detail="Username already registered")

    db_user = Student(
        username=user_in.username,
        full_name=user_in.full_name,
        hashed_password=get_password_hash(user_in.password)
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Check AuthorizedUser table first
    user = db.query(AuthorizedUser).filter(AuthorizedUser.username == form_data.username).first()
    role = user.role if user else "User" # Default role for student
    
    if not user:
        # Check Student table
        user = db.query(Student).filter(Student.username == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": str(role),
        "full_name": user.full_name or ""},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}
