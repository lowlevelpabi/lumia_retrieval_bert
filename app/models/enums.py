import enum

class UserRole(str, enum.Enum):
    ADMIN = "Admin"
    FACULTY = "Faculty"
    USER = "User" # For Students
