export type CrmPipelineType = "saas_sales" | "supplier_acquisition";
export type CrmStage = "new" | "contacted" | "qualified" | "proposal" | "negotiation" | "won" | "lost";
export type CrmActivityType = "call" | "meeting" | "note" | "task";

export const CRM_STAGES: CrmStage[] = ["new", "contacted", "qualified", "proposal", "negotiation", "won", "lost"];

export interface CrmOrganization {
  id: string;
  name: string;
  pipeline_type: CrmPipelineType;
  stage: CrmStage;
  source: string | null;
  industry: string | null;
  website: string | null;
  phone: string | null;
  email: string | null;
  notes: string | null;
  owner_staff_id: string | null;
  owner_staff_name: string | null;
  converted_company_id: string | null;
  converted_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface CrmContact {
  id: string;
  organization_id: string;
  name: string;
  title: string | null;
  email: string | null;
  phone: string | null;
  is_primary: boolean;
}

export interface CrmActivity {
  id: string;
  organization_id: string;
  type: CrmActivityType;
  summary: string;
  due_at: string | null;
  completed_at: string | null;
  created_by_id: string;
  created_by_name: string | null;
  created_at: string;
}

export interface CrmOrganizationDetail extends CrmOrganization {
  contacts: CrmContact[];
  activities: CrmActivity[];
}

export interface CrmConvertResult {
  organization: CrmOrganization;
  company_id: string;
  already_converted: boolean;
}
