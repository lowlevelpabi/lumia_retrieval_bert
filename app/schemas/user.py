from pydantic import BaseModel, EmailStr
from typing import Optional
from app.models.enums import UserRole

class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    role: Optional[UserRole] = UserRole.USER

class UserCreate(UserBase):
    password: str

class UserCreateStaff(BaseModel):
    username: str
    email: EmailStr
    full_name: str
    role: UserRole # Admin or Faculty

class UserResponse(UserBase):
    id: int

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

class UserRoleUpdate(BaseModel):
    role: UserRole


class PasswordUpdate(BaseModel):
    current_password: str
    new_password: str