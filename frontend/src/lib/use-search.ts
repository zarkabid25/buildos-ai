import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export interface SearchResultItem {
  id: string;
  title: string;
  subtitle: string | null;
  link: string;
}

export interface SearchResults {
  query: string;
  total: number;
  projects: SearchResultItem[];
  tasks: SearchResultItem[];
  materials: SearchResultItem[];
  suppliers: SearchResultItem[];
  purchase_orders: SearchResultItem[];
  documents: SearchResultItem[];
  employees: SearchResultItem[];
}

export const SEARCH_SECTIONS: { key: keyof SearchResults; label: string }[] = [
  { key: "projects", label: "Projects" },
  { key: "tasks", label: "Tasks" },
  { key: "materials", label: "Materials" },
  { key: "suppliers", label: "Suppliers" },
  { key: "purchase_orders", label: "Purchase Orders" },
  { key: "documents", label: "Documents" },
  { key: "employees", label: "Employees" },
];

export function useGlobalSearch(query: string) {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["search", query],
    queryFn: () => api.get<SearchResults>(`/search?q=${encodeURIComponent(query)}`, accessToken ?? undefined),
    enabled: !!accessToken && query.trim().length >= 2,
  });
}
