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
    DRAFT = 'draft'
    SUBMITTED = 'submitted'
    UNDER_REVIEW = 'under_review'
    VERIFIED = 'verified'
    ACCEPTED = 'accepted'
    REJECTED = 'rejected'
    WITHDRAWN = 'withdrawn'
    FINAL_ACCEPTED = 'final_accepted'
    FINAL_REJECTED = 'final_rejected'


class GradingFor(str, Enum):
    ABSTRACT = 'abstract'
    BEST_PAPER = 'best_paper'
    AWARD = 'award'


class CyclePhase(str, Enum):
    SUBMISSION = "SUBMISSION"
    VERIFICATION = "VERIFICATION"
    FINAL = "FINAL"
    # New values for specific components
    ABSTRACT_SUBMISSION = "ABSTRACT_SUBMISSION"
    BEST_PAPER_SUBMISSION = "BEST_PAPER_SUBMISSION"
    AWARD_SUBMISSION = "AWARD_SUBMISSION"
    ABSTRACT_VERIFICATION = "ABSTRACT_VERIFICATION"
    BEST_PAPER_VERIFICATION = "BEST_PAPER_VERIFICATION"
    AWARD_VERIFICATION = "AWARD_VERIFICATION"
    ABSTRACT_FINAL = "ABSTRACT_FINAL"
    BEST_PAPER_FINAL = "BEST_PAPER_FINAL"
    AWARD_FINAL = "AWARD_FINAL"
