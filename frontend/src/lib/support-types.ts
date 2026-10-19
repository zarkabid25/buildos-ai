export type SupportTicketCategory = "billing" | "technical" | "account" | "marketplace" | "other";
export type SupportTicketPriority = "low" | "medium" | "high" | "urgent";
export type SupportTicketStatus = "open" | "in_progress" | "waiting_on_requester" | "resolved" | "closed";
export type SupportRequesterType = "company" | "supplier";
export type SupportAuthorType = "company_user" | "supplier_user" | "staff";

export interface SupportTicketMessage {
  id: string;
  body: string;
  is_internal: boolean;
  author_type: SupportAuthorType;
  author_name: string | null;
  created_at: string;
}

export interface SupportTicket {
  id: string;
  requester_type: SupportRequesterType;
  company_id: string | null;
  company_name: string | null;
  marketplace_supplier_id: string | null;
  marketplace_supplier_name: string | null;
  subject: string;
  category: SupportTicketCategory;
  priority: SupportTicketPriority;
  status: SupportTicketStatus;
  assigned_staff_id: string | null;
  assigned_staff_name: string | null;
  resolved_at: string | null;
  messages: SupportTicketMessage[];
  created_at: string;
}

export interface SupportTicketSummary {
  id: string;
  requester_type: SupportRequesterType;
  company_name: string | null;
  marketplace_supplier_name: string | null;
  subject: string;
  category: SupportTicketCategory;
  priority: SupportTicketPriority;
  status: SupportTicketStatus;
  created_at: string;
}
