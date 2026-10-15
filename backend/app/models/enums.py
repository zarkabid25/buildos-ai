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


class DocumentCategory(str, enum.Enum):
    CONTRACT = "contract"
    DRAWING = "drawing"
    BOQ = "boq"
    INVOICE = "invoice"
    REPORT = "report"
    QUOTATION = "quotation"
    OTHER = "other"


class AiProposalType(str, enum.Enum):
    MATERIAL_REQUEST = "material_request"


class AiProposalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class NotificationType(str, enum.Enum):
    TASK_ASSIGNED = "task_assigned"
    MATERIAL_REQUEST_PENDING = "material_request_pending"
    PURCHASE_ORDER_PENDING = "purchase_order_pending"
    AI_PROPOSAL_PENDING = "ai_proposal_pending"


class RfqStatus(str, enum.Enum):
    OPEN = "open"  # sent to suppliers, quotations being collected
    AWARDED = "awarded"  # a quotation was chosen and a PO drafted from it
    CANCELLED = "cancelled"


class PaymentMethod(str, enum.Enum):
    BANK_TRANSFER = "bank_transfer"
    CHEQUE = "cheque"
    CASH = "cash"
    OTHER = "other"


class PlatformStaffRole(str, enum.Enum):
    """Platform staff permissions (PLAT-006). Separate from the tenant UserRole --
    a platform staff account is never a tenant User and vice versa."""

    OWNER = "owner"  # can also manage other staff (invite, change role, deactivate)
    ADMIN = "admin"  # can approve/suspend companies; cannot manage staff
    SUPPORT = "support"  # read-only


class CompanyOnboardingStatus(str, enum.Enum):
    """Tracked by platform staff only -- does not gate tenant login or
    registration. A new company starts 'pending'; every company that existed
    before this field was added is backfilled to 'approved' (migration 0023)."""

    PENDING = "pending"
    APPROVED = "approved"


class CrmPipelineType(str, enum.Enum):
    """Which pipeline a CRM organization is being worked through (PLAT-011..015).
    Both pipelines share one stage set (CrmStage) -- structurally similar sales
    processes -- labelled differently per pipeline in the UI."""

    SAAS_SALES = "saas_sales"
    SUPPLIER_ACQUISITION = "supplier_acquisition"


class CrmStage(str, enum.Enum):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    WON = "won"
    LOST = "lost"


class CrmActivityType(str, enum.Enum):
    CALL = "call"
    MEETING = "meeting"
    NOTE = "note"
    TASK = "task"  # a follow-up/reminder when due_at is set


class MarketplaceSupplierStatus(str, enum.Enum):
    """Verification workflow (PLAT-018). PENDING -> VERIFIED or REJECTED;
    VERIFIED -> SUSPENDED -> VERIFIED (reactivated). Transitions are enforced
    in the service layer, not the database."""

    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    SUSPENDED = "suspended"
