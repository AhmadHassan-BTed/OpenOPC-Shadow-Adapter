export type ShadowTaskStatus =
  | 'pending'
  | 'claimed'
  | 'submitted'
  | 'resumed'
  | 'failed'
  | 'cancelled';

export interface ShadowTask {
  id: string;
  opc_task_id: string;
  opc_session_id?: string;
  opc_project_id: string;
  opc_work_item_id: string;
  opc_metadata: Record<string, any>;
  title: string;
  description: string;
  assigned_role: string;
  priority: number;
  status: ShadowTaskStatus;
  assigned_contractor_id?: string;
  deliverable_text?: string;
  deliverable_files: string[];
  parked_at: string;
  claimed_at?: string;
  submitted_at?: string;
  resumed_at?: string;
  deadline?: string;
  extra_metadata: Record<string, any>;
}

export interface ContractorPublic {
  id: string;
  username: string;
  email?: string;
  display_name: string;
  roles: string[];
  is_active: boolean;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  contractor: ContractorPublic;
}

export interface TaskSubmitResponse {
  shadow_task_id: string;
  status: string;
  opc_resume_status: string;
  message: string;
}

export interface ShadowAuditEntry {
  id: number;
  shadow_task_id: string;
  actor_id?: string;
  action: string;
  details: Record<string, any>;
  created_at: string;
}

export interface HealthResponse {
  status: string;
  db: string;
  pending_tasks: number;
  version: string;
}
