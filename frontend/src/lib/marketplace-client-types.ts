export type MarketplaceSupplierStatus = "pending" | "verified" | "rejected" | "suspended";

export interface DiscoverySupplier {
  id: string;
  name: string;
  categories: string[];
  coverage_areas: string[];
  verification_status: MarketplaceSupplierStatus;
  is_connected: boolean;
  is_preferred: boolean;
}

export interface DiscoveryProduct {
  id: string;
  name: string;
  category: string | null;
  unit: string;
  price: string;
  minimum_order_quantity: string;
  lead_time_days: number | null;
}

export interface DiscoverySupplierDetail extends DiscoverySupplier {
  products: DiscoveryProduct[];
}

export interface CompanySupplierConnection {
  id: string;
  marketplace_supplier_id: string;
  marketplace_supplier_name: string | null;
  erp_supplier_id: string | null;
  is_preferred: boolean;
  status: string;
  notes: string | null;
  created_at: string;
}
