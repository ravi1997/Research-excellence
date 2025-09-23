# enums.py
from enum import Enum


class UserType(str, Enum):
    EMPLOYEE = 'employee'
    GENERAL = 'general'


class Role(str, Enum):
    SUPERADMIN = 'superadmin'
    ADMIN = 'admin'
    USER = 'user'
    VERIFIER = 'verifier'

class THEME_CHOICES(str, Enum):
    LIGHT = 'light'
    DARK = 'dark'
    SYSTEM = 'system'
    
class Status(str, Enum):
    PENDING = 'pending'
    UNDER_REVIEW = 'under_review'
    ACCEPTED = 'accepted'
    REJECTED = 'rejected'