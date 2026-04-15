from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.api.deps import admin_required, get_current_user
from app.models.user import Student
from app.models.authorized_user import AuthorizedUser, UserRole
from app.models.paper import Paper
from app.models.citation import UserCitation
from app.models.bookmark import UserBookmark
from app.schemas.paper import PaperResponse
from app.schemas.user import UserResponse, UserRoleUpdate, UserCreateStaff, PasswordUpdate
from app.core.security import verify_password, get_password_hash

router = APIRouter()

@router.get("/me", response_model=UserResponse)
def get_me(current_user: Student = Depends(get_current_user)):
    """
    Get current logged-in user details.
    """
    # current_user could be Student or AuthorizedUser, both match UserResponse
    if hasattr(current_user, 'role'):
        return current_user
    # If Student, role is implicitly User
    res = UserResponse.from_orm(current_user)
    res.role = UserRole.STUDENT
    return res

@router.get("/me/citations", response_model=List[PaperResponse])
def get_my_citations(
    current_user: Student = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a list of papers the current user has cited.
    """
    # citations works for both as they both have id
    citations = db.query(Paper).join(UserCitation).filter(UserCitation.user_id == current_user.id).all()
    return citations

@router.get("/me/bookmarks", response_model=List[PaperResponse])
def get_my_bookmarks(
    current_user: Student = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a list of papers the current user has bookmarked.
    """
    bookmarks = db.query(Paper).join(UserBookmark).filter(UserBookmark.user_id == current_user.id).all()
    return bookmarks

@router.get("/me/uploads", response_model=List[PaperResponse])
def get_my_uploads(
    current_user: Student = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Filter papers where the uploaded_by matches the current user's name
    name = current_user.full_name or current_user.username
    uploads = db.query(Paper).filter(
        Paper.uploaded_by == name,
        Paper.deleted_at.is_(None)
    ).all()
    
    return uploads


@router.patch("/me/password", status_code=204)
def update_my_password(
    body: PasswordUpdate,
    current_user: Student = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update the current user's password.
    Verifies the current password before applying the change.
    Works for both Student and AuthorizedUser accounts.
    """
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")

    new_hash = get_password_hash(body.new_password)

    # Determine which table the user belongs to and update accordingly
    staff = db.query(AuthorizedUser).filter(AuthorizedUser.id == current_user.id).first()
    if staff:
        staff.hashed_password = new_hash
    else:
        student = db.query(Student).filter(Student.id == current_user.id).first()
        if not student:
            raise HTTPException(status_code=404, detail="User not found.")
        student.hashed_password = new_hash

    db.commit()

@router.get("/", response_model=List[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    admin_user: AuthorizedUser = Depends(admin_required)
):
    """
    Get all users. Only accessible by admins.
    """
    staff = db.query(AuthorizedUser).all()
    students = db.query(Student).all()
    
    combined = []
    for s in staff:
        combined.append(s)
    for st in students:
        combined.append(st)
        
    return combined

@router.patch("/{user_id}/role", response_model=UserResponse)
def change_user_role(
    user_id: str,
    body: UserRoleUpdate,
    db: Session = Depends(get_db),
    admin_user: AuthorizedUser = Depends(admin_required)
):
    # Only support role changes for AuthorizedUser for now
    # Student promotion would involve moving records, which is more complex
    user = db.query(AuthorizedUser).filter(AuthorizedUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Staff user not found for role change")
    
    user.role = body.role
    db.commit()
    db.refresh(user)
    return user

@router.post("/staff", response_model=dict)
def create_staff_user(
    body: UserCreateStaff,
    db: Session = Depends(get_db),
    admin_user: AuthorizedUser = Depends(admin_required)
):
    """
    Create a new staff/faculty account in authorized_users table.
    """
    from fastapi import HTTPException
    import secrets
    from app.core.security import get_password_hash # Changed from app.core.hash to app.core.security

    # Check if user already exists in EITHER table
    if db.query(AuthorizedUser).filter(AuthorizedUser.username == body.username).first() or \
       db.query(Student).filter(Student.username == body.username).first():
        raise HTTPException(status_code=400, detail="Username already registered")

    # Only allow Admin or Faculty roles
    if body.role not in [UserRole.ADMIN, UserRole.FACULTY]:
        raise HTTPException(status_code=400, detail="Only Admin or Faculty roles can be created here")

    # Generate random password
    generated_password = secrets.token_urlsafe(10)
    hashed_password = get_password_hash(generated_password)

    new_user = AuthorizedUser(
        username=body.username,
        full_name=body.full_name,
        hashed_password=hashed_password,
        role=body.role.value if hasattr(body.role, 'value') else body.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "user": UserResponse.from_orm(new_user),
        "password": generated_password
    }