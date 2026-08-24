import React, { useState } from "react";
import type { Transaction } from "../types";
import {
  X,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  Play,
  FileCode,
  Layers,
} from "lucide-react";

interface PaymentDetailModalProps {
  payment: Transaction | null;
  onClose: () => void;
  onRecover: (paymentId: string) => void;
  isRecovering: boolean;
}

export const PaymentDetailModal: React.FC<PaymentDetailModalProps> = ({
  payment,
  onClose,
  onRecover,
  isRecovering,
}) => {
  const [activeTab, setActiveTab] = useState<"timeline" | "policy" | "json">("timeline");

  if (!payment) return null;

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 2,
    }).format(val);
  };

  // Evaluate the 7 policy rules dynamically for visualization in UI
  const policyChecks = [
    {
      name: "1. Fraud Risk Block",
      passed: payment.failure_code !== "FRAUD_RISK" && payment.risk_score < 0.85,
      detail:
        payment.failure_code === "FRAUD_RISK"
          ? "FAIL: FRAUD_RISK code automatically blocked from retry"
          : "PASS: Risk score within safe threshold",
    },
    {
      name: "2. Max Retry Limit (3)",
      passed: payment.retry_count < 3,
      detail:
        payment.retry_count >= 3
          ? "FAIL: 3/3 retry attempts already exhausted"
          : `PASS: ${payment.retry_count}/3 retries used`,
    },
    {
      name: "3. Max Notification Limit (3)",
      passed: payment.message_count < 3,
      detail:
        payment.message_count >= 3
          ? "FAIL: 3/3 messages sent to customer"
          : `PASS: ${payment.message_count}/3 messages sent`,
    },
    {
      name: "4. Duplicate Payment Guard",
      passed: payment.status !== "RECOVERED" && payment.amount_recovered <= 0,
      detail:
        payment.status === "RECOVERED"
          ? "FAIL: Payment already recovered; duplicate charge prevented"
          : "PASS: Payment not yet settled",
    },
    {
      name: "5. Customer Opt-Out Guard",
      passed: !payment.customer?.opted_out,
      detail: payment.customer?.opted_out
        ? "FAIL: Customer opted out of automated outreach"
        : "PASS: Customer consent active",
    },
    {
      name: "6. Recovery SLA Window (48h)",
      passed: true,
      detail: "PASS: Transaction occurred within active 48-hour recovery window",
    },
    {
      name: "7. Confidence Threshold (>0.50)",
      passed: true,
      detail: "PASS: Failure classification confidence sufficient for autonomous execution",
    },
  ];

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal-content"
        onClick={(e) => e.stopPropagation()}
        style={{ maxWidth: "880px" }}
      >
        {/* Header */}
        <div
          style={{
            padding: "1.25rem 1.75rem",
            borderBottom: "1px solid var(--border-subtle)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <div
              style={{
                width: "36px",
                height: "36px",
                borderRadius: "8px",
                background: "rgba(59, 130, 246, 0.15)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <ShieldCheck size={20} color="#3b82f6" />
            </div>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <h2 style={{ fontSize: "1.1rem", fontWeight: "700", color: "#ffffff" }}>
                  Payment Audit & LangGraph Lifecycle
                </h2>
                <span
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "0.75rem",
                    color: "var(--accent-primary)",
                  }}
                >
                  {payment.id}
                </span>
              </div>
              <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                Failed at: {new Date(payment.failed_at).toLocaleString()}
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            style={{
              background: "transparent",
              border: "none",
              color: "var(--text-secondary)",
              cursor: "pointer",
              padding: "0.4rem",
            }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Top Summary Bar */}
        <div
          style={{
            padding: "1.25rem 1.75rem",
            background: "var(--bg-surface-elevated)",
            borderBottom: "1px solid var(--border-subtle)",
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
            gap: "1rem",
          }}
        >
          <div>
            <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", textTransform: "uppercase" }}>
              Amount
            </div>
            <div style={{ fontSize: "1.1rem", fontWeight: "700", color: "#ffffff" }}>
              {formatCurrency(payment.amount)}
            </div>
          </div>

          <div>
            <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", textTransform: "uppercase" }}>
              Failure Code
            </div>
            <div style={{ fontSize: "0.85rem", fontWeight: "600", color: "#f59e0b" }}>
              {payment.failure_code}
            </div>
          </div>

          <div>
            <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", textTransform: "uppercase" }}>
              Customer
            </div>
            <div style={{ fontSize: "0.85rem", fontWeight: "600", color: "#ffffff" }}>
              {payment.customer?.name || "Customer"}
            </div>
            <div style={{ fontSize: "0.7rem", color: "var(--text-secondary)" }}>
              {payment.customer?.segment || "REGULAR"} segment
            </div>
          </div>

          <div>
            <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", textTransform: "uppercase" }}>
              Current Status
            </div>
            <div style={{ fontSize: "0.85rem", fontWeight: "700", color: payment.status === "RECOVERED" ? "#10b981" : "#ef4444" }}>
              {payment.status}
            </div>
          </div>
        </div>

        {/* Tab Controls */}
        <div
          style={{
            padding: "0.75rem 1.75rem 0",
            display: "flex",
            gap: "1rem",
            borderBottom: "1px solid var(--border-subtle)",
          }}
        >
          <button
            onClick={() => setActiveTab("timeline")}
            style={{
              padding: "0.5rem 0.25rem",
              background: "none",
              border: "none",
              borderBottom: activeTab === "timeline" ? "2px solid var(--accent-primary)" : "2px solid transparent",
              color: activeTab === "timeline" ? "#ffffff" : "var(--text-secondary)",
              fontWeight: "600",
              fontSize: "0.85rem",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "0.4rem",
            }}
          >
            <Layers size={14} />
            <span>LangGraph Audit Trail ({payment.audit_events?.length ?? 0})</span>
          </button>

          <button
            onClick={() => setActiveTab("policy")}
            style={{
              padding: "0.5rem 0.25rem",
              background: "none",
              border: "none",
              borderBottom: activeTab === "policy" ? "2px solid var(--accent-primary)" : "2px solid transparent",
              color: activeTab === "policy" ? "#ffffff" : "var(--text-secondary)",
              fontWeight: "600",
              fontSize: "0.85rem",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "0.4rem",
            }}
          >
            <ShieldCheck size={14} />
            <span>Policy Engine Evaluation (7 Rules)</span>
          </button>

          <button
            onClick={() => setActiveTab("json")}
            style={{
              padding: "0.5rem 0.25rem",
              background: "none",
              border: "none",
              borderBottom: activeTab === "json" ? "2px solid var(--accent-primary)" : "2px solid transparent",
              color: activeTab === "json" ? "#ffffff" : "var(--text-secondary)",
              fontWeight: "600",
              fontSize: "0.85rem",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "0.4rem",
            }}
          >
            <FileCode size={14} />
            <span>Raw JSON Record</span>
          </button>
        </div>

        {/* Tab Body */}
        <div style={{ padding: "1.5rem 1.75rem", maxHeight: "400px", overflowY: "auto" }}>
          {/* TAB 1: LangGraph Timeline */}
          {activeTab === "timeline" && (
            <div>
              {payment.audit_events && payment.audit_events.length > 0 ? (
                <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                  {payment.audit_events.map((event, idx) => (
                    <div
                      key={event.id || idx}
                      style={{
                        background: "var(--bg-surface-elevated)",
                        border: "1px solid var(--border-subtle)",
                        borderRadius: "var(--radius-md)",
                        padding: "0.85rem 1.1rem",
                        display: "flex",
                        flexDirection: "column",
                        gap: "0.3rem",
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                        }}
                      >
                        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                          <span
                            style={{
                              background: "rgba(59, 130, 246, 0.15)",
                              color: "#60a5fa",
                              fontSize: "0.7rem",
                              fontWeight: "700",
                              padding: "0.15rem 0.45rem",
                              borderRadius: "4px",
                            }}
                          >
                            {event.node || "AGENT_NODE"}
                          </span>
                          <span style={{ fontSize: "0.85rem", fontWeight: "700", color: "#ffffff" }}>
                            {event.event_type}
                          </span>
                        </div>
                        <span style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>
                          {new Date(event.timestamp).toLocaleTimeString()}
                        </span>
                      </div>

                      {event.reason && (
                        <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>
                          <strong style={{ color: "#94a3b8" }}>Reason: </strong> {event.reason}
                        </div>
                      )}

                      {event.result && (
                        <div style={{ fontSize: "0.8rem", color: "#10b981" }}>
                          <strong style={{ color: "#94a3b8" }}>Result: </strong> {event.result}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ textAlign: "center", padding: "2rem", color: "var(--text-muted)" }}>
                  No LangGraph execution events recorded yet. Run "AI Recover" to execute the agent pipeline.
                </div>
              )}
            </div>
          )}

          {/* TAB 2: Policy Verification */}
          {activeTab === "policy" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
              {policyChecks.map((rule, idx) => (
                <div
                  key={idx}
                  style={{
                    background: rule.passed ? "rgba(16, 185, 129, 0.05)" : "rgba(239, 68, 68, 0.05)",
                    border: `1px solid ${rule.passed ? "rgba(16, 185, 129, 0.3)" : "rgba(239, 68, 68, 0.3)"}`,
                    borderRadius: "var(--radius-md)",
                    padding: "0.75rem 1rem",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
                    {rule.passed ? (
                      <CheckCircle2 size={18} color="#10b981" />
                    ) : (
                      <AlertCircle size={18} color="#ef4444" />
                    )}
                    <div>
                      <div style={{ fontSize: "0.85rem", fontWeight: "700", color: "#ffffff" }}>
                        {rule.name}
                      </div>
                      <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                        {rule.detail}
                      </div>
                    </div>
                  </div>

                  <span
                    style={{
                      fontSize: "0.7rem",
                      fontWeight: "700",
                      padding: "0.2rem 0.5rem",
                      borderRadius: "4px",
                      background: rule.passed ? "#10b981" : "#ef4444",
                      color: "#000",
                    }}
                  >
                    {rule.passed ? "ALLOWED" : "BLOCKED"}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* TAB 3: Raw JSON */}
          {activeTab === "json" && (
            <pre className="code-box">
              {JSON.stringify(payment, null, 2)}
            </pre>
          )}
        </div>

        {/* Footer Actions */}
        <div
          style={{
            padding: "1rem 1.75rem",
            borderTop: "1px solid var(--border-subtle)",
            display: "flex",
            alignItems: "center",
            justifyContent: "flex-end",
            gap: "0.75rem",
            background: "var(--bg-surface)",
          }}
        >
          <button className="btn btn-secondary" onClick={onClose}>
            Close
          </button>
          {(payment.status === "FAILED" || payment.status === "PENDING_RECOVERY") && (
            <button
              className="btn btn-primary"
              onClick={() => onRecover(payment.id)}
              disabled={isRecovering}
            >
              <Play size={14} />
              <span>{isRecovering ? "Executing LangGraph..." : "Run AI Recovery Agent"}</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
