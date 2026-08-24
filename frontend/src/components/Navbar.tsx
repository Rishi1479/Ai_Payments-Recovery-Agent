import React from "react";
import {
  ShieldCheck,
  Zap,
  Database,
  RefreshCw,
  Sliders,
} from "lucide-react";

interface NavbarProps {
  onTriggerBatch: () => void;
  onOpenSimulator: () => void;
  onSeedData: () => void;
  onRefresh: () => void;
  isRefreshing: boolean;
  isSeeding: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  onTriggerBatch,
  onOpenSimulator,
  onSeedData,
  onRefresh,
  isRefreshing,
  isSeeding,
}) => {
  return (
    <header
      style={{
        background: "rgba(14, 21, 38, 0.85)",
        backdropFilter: "blur(12px)",
        borderBottom: "1px solid var(--border-subtle)",
        position: "sticky",
        top: 0,
        zIndex: 100,
        padding: "0.85rem 2rem",
      }}
    >
      <div
        style={{
          maxWidth: "1600px",
          margin: "0 auto",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        {/* Brand */}
        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          <div
            style={{
              width: "40px",
              height: "40px",
              borderRadius: "10px",
              background: "linear-gradient(135deg, #0284c7 0%, #2563eb 100%)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: "0 0 15px rgba(37, 99, 235, 0.5)",
            }}
          >
            <ShieldCheck size={24} color="#ffffff" />
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <h1
                style={{
                  fontSize: "1.15rem",
                  fontWeight: "700",
                  letterSpacing: "-0.02em",
                  color: "#ffffff",
                }}
              >
                Razorpay AI Recovery Agent
              </h1>
              <span
                style={{
                  background: "rgba(59, 130, 246, 0.15)",
                  color: "#60a5fa",
                  fontSize: "0.65rem",
                  fontWeight: "700",
                  padding: "0.15rem 0.45rem",
                  borderRadius: "999px",
                  border: "1px solid rgba(59, 130, 246, 0.3)",
                }}
              >
                LANGGRAPH v2.0
              </span>
            </div>
            <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
              Autonomous Revenue Recovery • Hard Policy Engine • Adaptive Retries
            </p>
          </div>
        </div>

        {/* Live Status & Actions */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.85rem" }}>
          {/* Agent Engine Status Indicator */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.45rem",
              background: "var(--bg-surface-elevated)",
              padding: "0.4rem 0.75rem",
              borderRadius: "var(--radius-full)",
              border: "1px solid var(--border-subtle)",
              fontSize: "0.75rem",
              color: "var(--text-secondary)",
            }}
          >
            <span
              style={{
                width: "8px",
                height: "8px",
                borderRadius: "50%",
                background: "#10b981",
                boxShadow: "0 0 8px #10b981",
              }}
            />
            <span>Engine Active</span>
          </div>

          {/* Refresh Button */}
          <button
            className="btn btn-secondary btn-sm"
            onClick={onRefresh}
            disabled={isRefreshing}
            title="Refresh analytics and table"
          >
            <RefreshCw
              size={14}
              style={{
                animation: isRefreshing ? "spin 1s linear infinite" : "none",
              }}
            />
            <span>{isRefreshing ? "Updating..." : "Refresh"}</span>
          </button>

          {/* Seed Dataset */}
          <button
            className="btn btn-secondary btn-sm"
            onClick={onSeedData}
            disabled={isSeeding}
            title="Generate synthetic payment failures"
          >
            <Database size={14} />
            <span>{isSeeding ? "Seeding..." : "Seed 300 Payments"}</span>
          </button>

          {/* Simulator */}
          <button
            className="btn btn-secondary btn-sm"
            onClick={onOpenSimulator}
            title="Inject test failure"
          >
            <Sliders size={14} />
            <span>Inject Failure</span>
          </button>

          {/* Batch Run Button */}
          <button
            className="btn btn-primary btn-sm"
            onClick={onTriggerBatch}
            style={{
              background: "linear-gradient(135deg, #2563eb 0%, #7c3aed 100%)",
            }}
          >
            <Zap size={14} />
            <span>Run Batch Recovery</span>
          </button>
        </div>
      </div>
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </header>
  );
};
