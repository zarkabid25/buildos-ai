import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export interface AiStatus {
  configured: boolean;
  provider: string;
  model: string;
}

export interface Insight {
  severity: "high" | "medium" | "low";
  category: string;
  title: string;
  detail: string;
  project_id: string | null;
  data: Record<string, unknown>;
}

export interface InsightsReport {
  generated_by: "rules";
  summary: string;
  counts: Record<string, number>;
  insights: Insight[];
}

export interface AiProposal {
  id: string;
  conversation_id: string | null;
  proposal_type: "material_request";
  status: "pending" | "approved" | "rejected";
  summary: string;
  payload: Record<string, unknown>;
  result_ref: string | null;
  created_at: string;
}

export interface ToolCall {
  name: string;
  input: Record<string, unknown>;
  is_error: boolean;
}

export interface ChatResponse {
  conversation_id: string;
  reply: string;
  tool_calls: ToolCall[];
  proposals: AiProposal[];
}

export function useAiStatus() {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["ai", "status"],
    queryFn: () => api.get<AiStatus>("/ai/status", accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useInsights() {
  const { accessToken } = useAuth();
  return useQuery({
    queryKey: ["ai", "insights"],
    queryFn: () => api.get<InsightsReport>("/ai/insights", accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useProposals(status?: AiProposal["status"]) {
  const { accessToken } = useAuth();
  const query = status ? `?status=${status}` : "";
  return useQuery({
    queryKey: ["ai", "proposals", status ?? "all"],
    queryFn: () => api.get<AiProposal[]>(`/ai/proposals${query}`, accessToken ?? undefined),
    enabled: !!accessToken,
  });
}

export function useChat() {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { message: string; conversation_id?: string }) =>
      api.post<ChatResponse>("/ai/chat", input, accessToken ?? undefined),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["ai", "proposals"] }),
  });
}

export function useDecideProposal() {
  const { accessToken } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, decision }: { id: string; decision: "approve" | "reject" }) =>
      api.post<AiProposal>(`/ai/proposals/${id}/${decision}`, {}, accessToken ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ai", "proposals"] });
      queryClient.invalidateQueries({ queryKey: ["material-requests"] });
      queryClient.invalidateQueries({ queryKey: ["ai", "insights"] });
    },
  });
}
