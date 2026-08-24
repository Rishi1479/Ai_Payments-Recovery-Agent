import React from "react";
import type { AnalyticsSummary } from "../types";
import {
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
  Cpu,
  RefreshCcw,
  UserCheck,
} from "lucide-react";

interface MetricsOverviewProps {
  summary: AnalyticsSummary | null;
  loading: boolean;
}

export const MetricsOverview: React.FC<MetricsOverviewProps> = ({
  summary,
  loading,
}) => {
  const formatCurrency = (val?: number) => {
    if (val === undefined || isNaN(val)) return "₹0";
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(val);
  };

  const cards = [
    {
      title: "Revenue Recovered",
      value: formatCurrency(summary?.total_revenue_recovered),
      subtext: `${summary?.total_payments_recovered ?? 0} transactions saved`,
      icon: <CheckCircle2 size={20} color="#10b981" />,
      color: "var(--color-success)",
      bgGlow: "rgba(16, 185, 129, 0.1)",
      border: "rgba(16, 185, 129, 0.3)",
    },
    {
      title: "Revenue at Risk",
      value: formatCurrency(summary?.total_revenue_at_risk),
      subtext: `${summary?.total_payments_failed ?? 0} failed payments ingested`,
      icon: <AlertTriangle size={20} color="#ef4444" />,
      color: "var(--color-danger)",
      bgGlow: "rgba(239, 68, 68, 0.1)",
      border: "rgba(239, 68, 68, 0.3)",
    },
    {
      title: "Recovery Rate",
      value: `${(summary?.recovery_rate ?? 0).toFixed(1)}%`,
      subtext: `Target SLA > 60%`,
      icon: <TrendingUp size={20} color="#3b82f6" />,
      color: "var(--accent-primary)",
      bgGlow: "rgba(59, 130, 246, 0.1)",
      border: "rgba(59, 130, 246, 0.3)",
    },
    {
      title: "Retry Success Rate",
      value: `${(summary?.retry_success_rate ?? 0).toFixed(1)}%`,
      subtext: `Adaptive retry backoff effectiveness`,
      icon: <RefreshCcw size={20} color="#f59e0b" />,
      color: "var(--color-warning)",
      bgGlow: "rgba(245, 158, 11, 0.1)",
      border: "rgba(245, 158, 11, 0.3)",
    },
    {
      title: "Classification Routing",
      value: `${(summary?.deterministic_classification_pct ?? 100).toFixed(0)}% / ${(summary?.llm_classification_pct ?? 0).toFixed(0)}%`,
      subtext: "Deterministic (0-token) vs LLM Agent",
      icon: <Cpu size={20} color="#8b5cf6" />,
      color: "var(--color-purple)",
      bgGlow: "rgba(139, 92, 246, 0.1)",
      border: "rgba(139, 92, 246, 0.3)",
    },
    {
      title: "Human / Escalation",
      value: `${(summary?.total_payments_human_review ?? 0) + (summary?.total_payments_escalated ?? 0)}`,
      subtext: `${summary?.total_payments_human_review ?? 0} human review • ${summary?.total_payments_escalated ?? 0} escalated`,
      icon: <UserCheck size={20} color="#06b6d4" />,
      color: "var(--color-cyan)",
      bgGlow: "rgba(6, 182, 212, 0.1)",
      border: "rgba(6, 182, 212, 0.3)",
    },
  ];

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
        gap: "1.25rem",
      }}
    >
      {cards.map((card, idx) => (
        <div
          key={idx}
          className="glass-card"
          style={{
            padding: "1.25rem 1.5rem",
            position: "relative",
            overflow: "hidden",
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
            borderLeft: `4px solid ${card.color}`,
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              marginBottom: "0.75rem",
            }}
          >
            <span
              style={{
                fontSize: "0.8rem",
                fontWeight: "600",
                color: "var(--text-secondary)",
                textTransform: "uppercase",
                letterSpacing: "0.04em",
              }}
            >
              {card.title}
            </span>
            <div
              style={{
                width: "36px",
                height: "36px",
                borderRadius: "8px",
                background: card.bgGlow,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              {card.icon}
            </div>
          </div>

          <div>
            <div
              style={{
                fontSize: "1.65rem",
                fontWeight: "800",
                color: "#ffffff",
                letterSpacing: "-0.03em",
                fontVariantNumeric: "tabular-nums",
                marginBottom: "0.25rem",
              }}
            >
              {loading ? (
                <span
                  style={{
                    display: "inline-block",
                    width: "80px",
                    height: "28px",
                    background: "var(--bg-surface-elevated)",
                    borderRadius: "4px",
                    animation: "pulse 1.5s infinite",
                  }}
                />
              ) : (
                card.value
              )}
            </div>
            <div
              style={{
                fontSize: "0.75rem",
                color: "var(--text-muted)",
              }}
            >
              {card.subtext}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};
