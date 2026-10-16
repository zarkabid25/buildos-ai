export type MarketplaceSupplierStatus = "pending" | "verified" | "rejected" | "suspended";

export interface MarketplaceSupplier {
  id: string;
  name: string;
  legal_name: string | null;
  email: string | null;
  phone: string | null;
  website: string | null;
  address: string | null;
  notes: string | null;
  verification_status: MarketplaceSupplierStatus;
  onboarded_by_id: string;
  onboarded_by_name: string | null;
  categories: string[];
  coverage_areas: string[];
  created_at: string;
  updated_at: string;
}

export interface MarketplaceSupplierCreated {
  supplier: MarketplaceSupplier;
  possible_duplicates: MarketplaceSupplier[];
}

export interface MarketplaceSupplierList {
  total: number;
  suppliers: MarketplaceSupplier[];
}

export interface MarketplaceContact {
  id: string;
  supplier_id: string;
  name: string;
  role: string | null;
  email: string | null;
  phone: string | null;
  is_primary: boolean;
}

export interface MarketplaceDocument {
  id: string;
  supplier_id: string;
  title: string;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  uploaded_by_id: string;
  created_at: string;
}

export interface MarketplaceProduct {
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

export interface MarketplaceSupplierDetail extends MarketplaceSupplier {
  contacts: MarketplaceContact[];
  documents: MarketplaceDocument[];
  products: MarketplaceProduct[];
}

export interface MarketplaceCompanyLink {
  id: string;
  company_id: string;
  company_name: string | null;
  marketplace_supplier_id: string;
  linked_by_id: string;
  notes: string | null;
  created_at: string;
}

export interface CompanyRfqSummary {
  id: string;
  rfq_number: string;
  title: string;
  project_name: string | null;
  status: "open" | "awarded" | "cancelled";
  response_due: string | null;
  item_count: number;
  invited_count: number;
  quotation_count: number;
  lowest_total: string | null;
  created_at: string;
}

export interface CompanyRfqItem {
  id: string;
  material_id: string;
  material_name: string;
  unit: string;
  quantity: string;
}

export interface CompanyRfqDetail {
  id: string;
  rfq_number: string;
  title: string;
  status: "open" | "awarded" | "cancelled";
  items: CompanyRfqItem[];
}

export interface SupplierMatch {
  marketplace_supplier_id: string;
  supplier_name: string;
  verification_status: MarketplaceSupplierStatus;
  product_id: string;
  product_name: string;
  price: string;
  minimum_order_quantity: string;
  lead_time_days: number | null;
  coverage_areas: string[];
  matched_via: "material_mapping" | "category";
}
