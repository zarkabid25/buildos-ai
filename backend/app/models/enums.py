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
    SUPPORT_TICKET_REPLY = "support_ticket_reply"
    SUPPORT_TICKET_RESOLVED = "support_ticket_resolved"


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


class BillingPeriod(str, enum.Enum):
    MONTHLY = "monthly"
    ANNUAL = "annual"


class SubscriptionStatus(str, enum.Enum):
    """A real state machine (PLAT-029), enforced in subscription_service, not
    just a free-form status. TRIALING/ACTIVE/PENDING_PAYMENT/GRACE_PERIOD are
    the "live" states -- a company has at most one subscription row in any of
    these at a time, enforced at the database level (see CompanySubscription's
    partial unique index), not only by an application check."""

    TRIALING = "trialing"
    ACTIVE = "active"
    PENDING_PAYMENT = "pending_payment"
    GRACE_PERIOD = "grace_period"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


LIVE_SUBSCRIPTION_STATUSES = (
    SubscriptionStatus.TRIALING,
    SubscriptionStatus.ACTIVE,
    SubscriptionStatus.PENDING_PAYMENT,
    SubscriptionStatus.GRACE_PERIOD,
)


class InvoiceStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    PAID = "paid"
    REJECTED = "rejected"
    VOID = "void"


class PaymentSubmissionStatus(str, enum.Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


# ---- Phase 6: marketplace commissions (PLAT-033..037) -------------------------------------


class CommissionBasis(str, enum.Enum):
    PERCENTAGE = "percentage"
    FIXED_FEE = "fixed_fee"


class CommissionEarningTrigger(str, enum.Enum):
    # Only ON_PAYMENT is actually wired to accrue commission today -- see
    # commission_service's module docstring for why (verified-payment
    # attribution is the only reliable signal that exists in this schema).
    ON_PAYMENT = "on_payment"


class CommissionAgreementStatus(str, enum.Enum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    CANCELLED = "cancelled"


class CommissionLedgerEntryKind(str, enum.Enum):
    ACCRUAL = "accrual"
    REVERSAL = "reversal"
    ADJUSTMENT = "adjustment"


class CommissionInvoiceStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    VOID = "void"


class CommissionDisputeStatus(str, enum.Enum):
    OPEN = "open"
    APPROVED = "approved"
    REJECTED = "rejected"


# ---- Phase 7: supplier self-service portal (PLAT-038..042) ---------------------------------


class SupplierMembershipRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    STAFF = "staff"


class SupplierMembershipStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"


# ---- Phase 8: public website, onboarding and support (PLAT-043..047) -----------------------


class SupplierApplicationStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class SupportTicketCategory(str, enum.Enum):
    BILLING = "billing"
    TECHNICAL = "technical"
    ACCOUNT = "account"
    MARKETPLACE = "marketplace"
    OTHER = "other"


class SupportTicketPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class SupportTicketStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_ON_REQUESTER = "waiting_on_requester"
    RESOLVED = "resolved"
    CLOSED = "closed"


class SupportRequesterType(str, enum.Enum):
    COMPANY = "company"
    SUPPLIER = "supplier"


class SupportAuthorType(str, enum.Enum):
    COMPANY_USER = "company_user"
    SUPPLIER_USER = "supplier_user"
    STAFF = "staff"


class EmailDeliveryStatus(str, enum.Enum):
    """Honest about reality (Phase 8 brief, PLAT-047): this app has no SMTP
    provider configured. SENT is only ever recorded once a real provider
    actually accepts the message -- never assumed. NOT_CONFIGURED is the
    expected status in every environment today."""

    NOT_CONFIGURED = "not_configured"
    SENT = "sent"
    FAILED = "failed"
