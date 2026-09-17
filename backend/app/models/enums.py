import enum


class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    COMPANY_ADMIN = "company_admin"
    PROJECT_MANAGER = "project_manager"
    SITE_ENGINEER = "site_engineer"
    STOREKEEPER = "storekeeper"
    ACCOUNTANT = "accountant"
    VIEWER = "viewer"
