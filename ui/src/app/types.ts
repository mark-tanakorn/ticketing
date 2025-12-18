export interface Ticket {
  id: number;
  title: string;
  description: string;
  category: string;
  severity: string;
  date_created: string;
  status: string;
  attachment_upload: string;
  approver: string;
  fixer: string;
  approver_decision?: boolean;
  approver_reply_text?: string;
  approver_decided_at?: string;
  tav_execution_id?: string;
  sla_reminder_sent_at?: string;
  sla_breached_at?: string;
  sla_started_at?: string;
  sla_start_time?: string;
}

export interface User {
  id: number;
  name: string;
  phone: string;
  email: string;
  department: string;
  approval_tier: number;
}

export interface Fixer {
  id: number;
  name: string;
  email: string;
  phone: string;
  department: string;
}