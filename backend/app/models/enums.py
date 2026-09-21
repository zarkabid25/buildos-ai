import enum


class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    COMPANY_ADMIN = "company_admin"
    PROJECT_MANAGER = "project_manager"
    SITE_ENGINEER = "site_engineer"
    STOREKEEPER = "storekeeper"
    ACCOUNTANT = "accountant"
    VIEWER = "viewer"


class ProjectStatus(str, enum.Enum):
    PLANNING = "planning"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskStatus(str, enum.Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"


class TaskPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class InventoryTransactionType(str, enum.Enum):
    STOCK_IN = "stock_in"
    STOCK_OUT = "stock_out"
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"
    ALLOCATION = "allocation"


class MaterialRequestStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CONVERTED = "converted"


class PurchaseOrderStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    PARTIALLY_RECEIVED = "partially_received"
    RECEIVED = "received"
    CANCELLED = "cancelled"


class AttendanceStatus(str, enum.Enum):
    PRESENT = "present"
    ABSENT = "absent"
    HALF_DAY = "half_day"
    LEAVE = "leave"


class EquipmentStatus(str, enum.Enum):
    AVAILABLE = "available"
    IN_USE = "in_use"
    MAINTENANCE = "maintenance"
    RETIRED = "retired"
