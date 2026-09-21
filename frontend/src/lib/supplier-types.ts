export interface Supplier {
  id: string;
  name: string;
  address: string | null;
  phone: string | null;
  email: string | null;
  notes: string | null;
}

export interface SupplierContact {
  id: string;
  supplier_id: string;
  name: string;
  role: string | null;
  phone: string | null;
  email: string | null;
}
