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
