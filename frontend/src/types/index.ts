export type FailureCode =
  | "INSUFFICIENT_FUNDS"
  | "BANK_TIMEOUT"
  | "NETWORK_ERROR"
  | "EXPIRED_CARD"
  | "CARD_DECLINED"
  | "FRAUD_RISK"
  | "UNKNOWN";

export type FailureCategory =
  | "TEMPORARY_FUNDS"
  | "TEMPORARY_TECHNICAL"
  | "PAYMENT_METHOD_ISSUE"
  | "CARD_DECLINE"
  | "HIGH_RISK"
  | "UNKNOWN";

export type PaymentStatus =
  | "FAILED"
  | "PENDING_RECOVERY"
  | "RECOVERED"
  | "ESCALATED"
  | "EXHAUSTED"
  | "HUMAN_REVIEW";

export type RecoveryAction =
  | "RETRY"
  | "NOTIFY"
  | "ESCALATE"
  | "HUMAN_REVIEW"
  | "STOP";

export type PolicyResult = "APPROVED" | "BLOCKED";

export type ActionOutcome = "SUCCESS" | "FAILED" | "ALREADY_PAID" | "PENDING";

export type CustomerSegment = "PREMIUM" | "REGULAR" | "AT_RISK";

export type ClassificationMethod = "DETERMINISTIC" | "LLM";

export interface Customer {
  id: string;
  name: string;
  email: string;
  phone?: string;
  segment: CustomerSegment;
  previous_successful_payments: number;
  previous_failed_payments: number;
  total_amount_paid: number;
  opted_out: boolean;
  created_at: string;
}

export interface AuditEvent {
  id: string;
  transaction_id: string;
  event_type: string;
  node: string;
  reason?: string;
  result?: string;
  event_metadata: Record<string, any>;
  timestamp: string;
}

export interface RecoveryActionRecord {
  id: string;
  transaction_id: string;
  action_type: RecoveryAction;
  recommended_by: string;
  policy_result?: PolicyResult;
  policy_reason?: string;
  outcome: ActionOutcome;
  outcome_detail?: string;
  executed_at: string;
  completed_at?: string;
}

export interface ClassificationRecord {
  id: string;
  transaction_id: string;
  category: FailureCategory;
  confidence: number;
  reason?: string;
  method: ClassificationMethod;
  created_at: string;
}

export interface Transaction {
  id: string;
  customer_id: string;
  amount: number;
  currency: string;
  failure_code: FailureCode;
  failure_category?: FailureCategory;
  status: PaymentStatus;
  retry_count: number;
  message_count: number;
  risk_score: number;
  recovery_probability: number;
  revenue_at_risk: number;
  amount_recovered: number;
  escalation_reason?: string;
  failed_at: string;
  recovered_at?: string;
  created_at: string;
  updated_at: string;
  customer?: Customer;
  classifications?: ClassificationRecord[];
  recovery_actions?: RecoveryActionRecord[];
  audit_events?: AuditEvent[];
}

export interface AnalyticsSummary {
  total_revenue_at_risk: number;
  total_revenue_recovered: number;
  recovery_rate: number;
  retry_success_rate: number;
  total_payments_failed: number;
  total_payments_recovered: number;
  total_payments_escalated: number;
  total_payments_exhausted: number;
  total_payments_human_review: number;
  total_payments_pending: number;
  deterministic_classification_pct: number;
  llm_classification_pct: number;
  active_retries: number;
}

export interface FailureBreakdown {
  failure_code: string;
  total: number;
  recovered: number;
  recovery_rate: number;
  revenue_at_risk: number;
  revenue_recovered: number;
}

export interface DailyTrend {
  date: string;
  failed: number;
  recovered: number;
  revenue_at_risk: number;
  revenue_recovered: number;
}

export interface BatchRunResult {
  batch_id: string;
  total: number;
  recovered: number;
  escalated: number;
  exhausted: number;
  human_review: number;
  errors: number;
  revenue_recovered: number;
  elapsed_seconds: number;
  throughput_per_sec: number;
  avg_latency_ms: number;
}

export interface SingleRecoveryResult {
  payment_id: string;
  final_state: {
    status: PaymentStatus;
    recovered: boolean;
    revenue_recovered: number;
    decision: RecoveryAction;
    decision_reason: string;
    policy_approved: boolean;
    policy_reason?: string;
    risk_score: number;
    failure_category: FailureCategory;
    classification_method: ClassificationMethod;
    retries_count: number;
    messages_count: number;
    audit_events: AuditEvent[];
    logs: string[];
  };
}
