from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from typing import List, Union

from app.core.config import settings
from app.core.database import get_db
from app.models.user import Student
from app.models.authorized_user import AuthorizedUser, UserRole
from app.schemas.user import TokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> Union[Student, AuthorizedUser]:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username, role=payload.get("role"))
    except JWTError:
        raise credentials_exception
    
    # Try AuthorizedUser first
    user = db.query(AuthorizedUser).filter(AuthorizedUser.username == token_data.username).first()
    if not user:
        user = db.query(Student).filter(Student.username == token_data.username).first()
    
    if user is None:
        raise credentials_exception
    return user

class RoleChecker:
    def __init__(self, allowed_roles: List[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: Union[Student, AuthorizedUser] = Depends(get_current_user)):
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have enough privileges to perform this action"
            )
        return current_user

# Predefined role dependencies
admin_required = RoleChecker([UserRole.ADMIN])
faculty_or_admin_required = RoleChecker([UserRole.ADMIN, UserRole.FACULTY])
