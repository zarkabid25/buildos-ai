export type SupplierMembershipRole = "owner" | "admin" | "staff";
export type SupplierMembershipStatus = "active" | "suspended" | "revoked";
export type MarketplaceSupplierVerificationStatus = "pending" | "verified" | "rejected" | "suspended";

export interface SupplierUser {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
}

export interface SupplierMembershipSummary {
  marketplace_supplier_id: string;
  marketplace_supplier_name: string;
  role: SupplierMembershipRole;
  status: SupplierMembershipStatus;
}

export interface SupplierAuthResponse {
  access_token: string;
  refresh_token: string;
  active_supplier_id: string | null;
  user: SupplierUser;
  memberships: SupplierMembershipSummary[];
}

export interface SupplierInvitation {
  id: string;
  email: string;
  full_name: string | null;
  role: SupplierMembershipRole;
  invited_by_name: string | null;
  created_at: string;
  expires_at: string;
  expired: boolean;
}

export interface SupplierInvitationCreated extends SupplierInvitation {
  token: string;
}

export interface SupplierInvitationInfo {
  marketplace_supplier_name: string;
  email: string;
  full_name: string | null;
  role: SupplierMembershipRole;
}

export interface SupplierMembership {
  id: string;
  supplier_user_id: string;
  user_full_name: string;
  user_email: string;
  role: SupplierMembershipRole;
  status: SupplierMembershipStatus;
  created_at: string;
}

export interface SupplierDashboard {
  new_invitations: number;
  pending_quotations: number;
  submitted_quotations: number;
  active_linked_orders: number;
  pending_delivery_updates: number;
  outstanding_commission_invoices: number;
}

export interface SupplierPortalProfile {
  id: string;
  name: string;
  legal_name: string | null;
  email: string | null;
  phone: string | null;
  website: string | null;
  address: string | null;
  notes: string | null;
  verification_status: MarketplaceSupplierVerificationStatus;
  categories: string[];
  coverage_areas: string[];
}

export interface SupplierPortalDocument {
  id: string;
  title: string;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  created_at: string;
}

export interface SupplierPortalProduct {
  id: string;
  supplier_id: string;
  name: string;
  category: string | null;
  unit: string;
  price: string;
  minimum_order_quantity: string;
  lead_time_days: number | null;
  is_active: boolean;
  created_at: string;
}

export interface SupplierRfqInboxItem {
  invitation_id: string;
  rfq_id: string;
  rfq_number: string;
  title: string;
  company_name: string;
  status: "invited" | "quoted" | "declined";
  response_due: string | null;
  created_at: string;
}

export interface SupplierRfqItem {
  id: string;
  material_name: string;
  unit: string;
  quantity: string;
}

export interface SupplierOwnQuotationItem {
  rfq_item_id: string;
  rate: string;
  amount: string;
}

export interface SupplierOwnQuotation {
  id: string;
  delivery_days: number | null;
  valid_until: string | null;
  notes: string | null;
  total: string;
  created_at: string;
  items: SupplierOwnQuotationItem[];
}

export interface SupplierRfqDetail {
  rfq_id: string;
  rfq_number: string;
  title: string;
  company_name: string;
  notes: string | null;
  response_due: string | null;
  rfq_status: string;
  invitation_status: string;
  items: SupplierRfqItem[];
  my_quotation: SupplierOwnQuotation | null;
}

export interface SupplierQuotationHistoryItem {
  rfq_id: string;
  rfq_number: string;
  company_name: string;
  total: string;
  submitted_at: string;
}

export interface SupplierOrderItem {
  id: string;
  material_name: string;
  quantity: string;
  rate: string;
  quantity_received: string;
  amount: string;
}

export interface SupplierOrder {
  purchase_order_id: string;
  po_number: string;
  company_name: string;
  status: string;
  total_amount: string;
  amount_paid: string;
  created_at: string;
  items: SupplierOrderItem[];
}

export interface SupplierDeliveryUpdate {
  id: string;
  purchase_order_id: string;
  external_reference: string;
  note: string | null;
  created_at: string;
  already_recorded: boolean;
}
