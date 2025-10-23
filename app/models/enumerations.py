from enum import Enum
# enums.py


class UserType(str, Enum):
    EMPLOYEE = 'employee'
    GENERAL = 'general'


class Role(str, Enum):
    SUPERADMIN = 'superadmin'
    ADMIN = 'admin'
    USER = 'user'
    VERIFIER = 'verifier'
    COORDINATOR = 'coordinator'


class THEME_CHOICES(str, Enum):
    LIGHT = 'light'
    DARK = 'dark'
    SYSTEM = 'system'


class Status(str, Enum):
    PENDING = 'pending'
    UNDER_REVIEW = 'under_review'
    ACCEPTED = 'accepted'
    REJECTED = 'rejected'


class GradingFor(str, Enum):
    ABSTRACT = 'abstract'
    BEST_PAPER = 'best_paper'
    AWARD = 'award'


class CyclePhase(str, Enum):
    SUBMISSION = "SUBMISSION"
    VERIFICATION = "VERIFICATION"
    FINAL = "FINAL"
