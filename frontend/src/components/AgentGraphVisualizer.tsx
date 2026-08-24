import React, { useState } from "react";
import {
  Download,
  ShieldAlert,
  Brain,
  Compass,
  ShieldCheck,
  PlayCircle,
  Database,
  ArrowRight,
  Info,
} from "lucide-react";

interface NodeInfo {
  id: string;
  name: string;
  short: string;
  category: "ingest" | "intelligence" | "decision" | "safety" | "execution" | "persistence";
  icon: React.ReactNode;
  description: string;
  rules: string[];
}

const GRAPH_NODES: NodeInfo[] = [
  {
    id: "ingestion",
    name: "1. Ingestion & Profile Enrichment",
    short: "Ingestion",
    category: "ingest",
    icon: <Download size={18} color="#3b82f6" />,
    description: "Ingests raw webhook payload, checks customer history (previous successful vs failed), VIP segments, and opt-out flags.",
    rules: [
      "Load customer profile & payment history",
      "Check customer opt_out status",
      "Calculate customer historical LTV & segment",
    ],
  },
  {
    id: "risk_analysis",
    name: "2. Risk Scoring Node",
    short: "Risk Scorer",
    category: "intelligence",
    icon: <ShieldAlert size={18} color="#f59e0b" />,
    description: "Calculates composite risk score [0.0 - 1.0] from failure codes, customer track record, and payment velocity.",
    rules: [
      "FRAUD_RISK code -> 0.95 risk score",
      "New customer + high failure -> elevated risk",
      "High LTV + good history -> low risk score",
    ],
  },
  {
    id: "root_cause_classification",
    name: "3. Root Cause Classification",
    short: "Classification",
    category: "intelligence",
    icon: <Brain size={18} color="#8b5cf6" />,
    description: "Hybrid routing: Fast deterministic pattern matching (0-token, <1ms) with automatic fallback to Gemini LLM for ambiguous error strings.",
    rules: [
      "Deterministic: BANK_TIMEOUT, INSUFFICIENT_FUNDS, EXPIRED_CARD, CARD_DECLINED, FRAUD_RISK",
      "LLM Fallback: Parses messy ISO 8583 gateway error messages",
      "Outputs FailureCategory + confidence score",
    ],
  },
  {
    id: "recovery_decision",
    name: "4. Recovery Strategy Engine",
    short: "Decision Engine",
    category: "decision",
    icon: <Compass size={18} color="#06b6d4" />,
    description: "Evaluates root cause and risk score to recommend the optimal recovery tactic: RETRY, NOTIFY, ESCALATE, or HUMAN_REVIEW.",
    rules: [
      "TEMPORARY_TECHNICAL -> RETRY with adaptive backoff",
      "INSUFFICIENT_FUNDS / EXPIRED_CARD -> NOTIFY customer",
      "HIGH_RISK / FRAUD -> ESCALATE (never retry)",
      "Low confidence (<0.50) -> HUMAN_REVIEW",
    ],
  },
  {
    id: "policy_engine",
    name: "5. Hard Deterministic Policy Engine",
    short: "Policy Engine",
    category: "safety",
    icon: <ShieldCheck size={18} color="#ef4444" />,
    description: "CRITICAL SAFETY BOUNDARY: Strict hardcoded deterministic rules that CANNOT be bypassed by LLM or strategy engine.",
    rules: [
      "Rule 1: Block all retries on FRAUD_RISK / HIGH_RISK",
      "Rule 2: Enforce max 3 retry attempts per transaction",
      "Rule 3: Enforce max 3 customer notifications",
      "Rule 4: Prevent duplicate charges if already RECOVERED",
      "Rule 5: Zero outreach/retries if customer opted out",
      "Rule 6: Respect 48-hour recovery window SLA",
      "Rule 7: Force HUMAN_REVIEW for confidence < 0.50",
    ],
  },
  {
    id: "action_execution",
    name: "6. Gateway & Comm Execution",
    short: "Execution",
    category: "execution",
    icon: <PlayCircle size={18} color="#10b981" />,
    description: "Executes the policy-approved action against the Mock Payment Gateway or SMS/Email notification provider.",
    rules: [
      "Execute payment retry via gateway API",
      "Dispatch personalized SMS/WhatsApp payment link",
      "Record execution latency and outcome status",
    ],
  },
  {
    id: "outcome_evaluation",
    name: "7. State Sync & Audit Logging",
    short: "Audit & Sync",
    category: "persistence",
    icon: <Database size={18} color="#3b82f6" />,
    description: "Persists final status (RECOVERED, ESCALATED, EXHAUSTED) in PostgreSQL, computes recovered revenue, and writes immutable audit trail.",
    rules: [
      "Emit structured AuditEvents for every node",
      "Update transaction revenue_recovered and status",
      "Increment customer successful recovery metrics",
    ],
  },
];

interface AgentGraphVisualizerProps {
  activeNode?: string;
}

export const AgentGraphVisualizer: React.FC<AgentGraphVisualizerProps> = ({
  activeNode,
}) => {
  const [selectedNode, setSelectedNode] = useState<NodeInfo>(GRAPH_NODES[4]); // Default to Policy Engine

  return (
    <div className="glass-card" style={{ padding: "1.5rem" }}>
      {/* Title */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "1.25rem",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
          <Brain size={20} color="#8b5cf6" />
          <h2 style={{ fontSize: "1.1rem", fontWeight: "700", color: "#ffffff" }}>
            LangGraph Recovery Pipeline Architecture
          </h2>
        </div>
        <span
          style={{
            fontSize: "0.75rem",
            color: "var(--text-secondary)",
            background: "var(--bg-surface-elevated)",
            padding: "0.25rem 0.65rem",
            borderRadius: "var(--radius-full)",
            border: "1px solid var(--border-subtle)",
          }}
        >
          Click any node to inspect safety rules
        </span>
      </div>

      {/* Pipeline Nodes Row */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "0.5rem",
          overflowX: "auto",
          paddingBottom: "0.75rem",
          marginBottom: "1.25rem",
        }}
      >
        {GRAPH_NODES.map((node, index) => {
          const isSelected = selectedNode.id === node.id;
          const isActive = activeNode === node.id;

          return (
            <React.Fragment key={node.id}>
              <div
                onClick={() => setSelectedNode(node)}
                style={{
                  flex: "1 0 160px",
                  background: isSelected
                    ? "var(--bg-surface-elevated)"
                    : "rgba(14, 21, 38, 0.6)",
                  border: isSelected
                    ? "2px solid var(--accent-primary)"
                    : "1px solid var(--border-subtle)",
                  borderRadius: "var(--radius-md)",
                  padding: "0.85rem",
                  cursor: "pointer",
                  transition: "all 0.2s ease",
                  boxShadow: isSelected
                    ? "0 0 15px var(--accent-primary-glow)"
                    : "none",
                  position: "relative",
                }}
                className={isActive ? "agent-active-glow" : ""}
              >
                {isActive && (
                  <span
                    style={{
                      position: "absolute",
                      top: "-8px",
                      right: "8px",
                      background: "#10b981",
                      color: "#000",
                      fontSize: "0.6rem",
                      fontWeight: "800",
                      padding: "0.1rem 0.4rem",
                      borderRadius: "999px",
                      letterSpacing: "0.05em",
                    }}
                  >
                    LIVE
                  </span>
                )}
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "0.5rem",
                    marginBottom: "0.4rem",
                  }}
                >
                  {node.icon}
                  <span
                    style={{
                      fontSize: "0.8rem",
                      fontWeight: "700",
                      color: isSelected ? "#ffffff" : "var(--text-secondary)",
                    }}
                  >
                    {node.short}
                  </span>
                </div>
                <div
                  style={{
                    fontSize: "0.7rem",
                    color: "var(--text-muted)",
                    lineHeight: "1.2",
                    display: "-webkit-box",
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: "vertical",
                    overflow: "hidden",
                  }}
                >
                  {node.description}
                </div>
              </div>

              {index < GRAPH_NODES.length - 1 && (
                <ArrowRight
                  size={16}
                  color="var(--text-dim)"
                  style={{ flexShrink: 0 }}
                />
              )}
            </React.Fragment>
          );
        })}
      </div>

      {/* Selected Node Details Drawer */}
      <div
        style={{
          background: "var(--bg-surface-elevated)",
          border: "1px solid var(--border-subtle)",
          borderRadius: "var(--radius-md)",
          padding: "1.25rem",
          display: "flex",
          flexDirection: "column",
          gap: "0.75rem",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
            {selectedNode.icon}
            <h3 style={{ fontSize: "0.95rem", fontWeight: "700", color: "#ffffff" }}>
              {selectedNode.name}
            </h3>
          </div>
          <span
            style={{
              fontSize: "0.7rem",
              fontWeight: "600",
              textTransform: "uppercase",
              padding: "0.2rem 0.5rem",
              borderRadius: "4px",
              background:
                selectedNode.id === "policy_engine"
                  ? "rgba(239, 68, 68, 0.2)"
                  : "rgba(59, 130, 246, 0.2)",
              color:
                selectedNode.id === "policy_engine"
                  ? "#f87171"
                  : "#60a5fa",
              border:
                selectedNode.id === "policy_engine"
                  ? "1px solid rgba(239, 68, 68, 0.4)"
                  : "1px solid rgba(59, 130, 246, 0.4)",
            }}
          >
            {selectedNode.id === "policy_engine"
              ? "CRITICAL SAFETY BOUNDARY"
              : "WORKFLOW STAGE"}
          </span>
        </div>

        <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>
          {selectedNode.description}
        </p>

        <div>
          <div
            style={{
              fontSize: "0.75rem",
              fontWeight: "700",
              color: "var(--text-muted)",
              textTransform: "uppercase",
              marginBottom: "0.4rem",
            }}
          >
            Configured Policies & Verification Bounds:
          </div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
              gap: "0.4rem",
            }}
          >
            {selectedNode.rules.map((rule, idx) => (
              <div
                key={idx}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.5rem",
                  fontSize: "0.8rem",
                  color: "#cbd5e1",
                  background: "rgba(0,0,0,0.25)",
                  padding: "0.35rem 0.65rem",
                  borderRadius: "4px",
                  borderLeft: "2px solid var(--accent-primary)",
                }}
              >
                <Info size={12} color="var(--accent-primary)" />
                <span>{rule}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
