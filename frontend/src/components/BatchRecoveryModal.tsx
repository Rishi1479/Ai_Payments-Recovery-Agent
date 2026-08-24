import { useState } from "react";
import confetti from "canvas-confetti";
import type { BatchRunResult } from "../types";
import {
  Zap,
  X,
  Sparkles,
} from "lucide-react";

interface BatchRecoveryModalProps {
  isOpen: boolean;
  onClose: () => void;
  onRunBatch: (params: { concurrency: number; llm_concurrency: number }) => Promise<BatchRunResult>;
}

export const BatchRecoveryModal: React.FC<BatchRecoveryModalProps> = ({
  isOpen,
  onClose,
  onRunBatch,
}) => {
  const [concurrency, setConcurrency] = useState(25);
  const [llmConcurrency, setLlmConcurrency] = useState(5);
  const [isRunning, setIsRunning] = useState(false);
  const [result, setResult] = useState<BatchRunResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleStart = async () => {
    setIsRunning(true);
    setError(null);
    setResult(null);

    try {
      const res = await onRunBatch({
        concurrency,
        llm_concurrency: llmConcurrency,
      });
      setResult(res);

      if (res.recovered > 0) {
        confetti({
          particleCount: 100,
          spread: 70,
          origin: { y: 0.6 },
        });
      }
    } catch (err: any) {
      setError(err.message || "Failed to execute batch run");
    } finally {
      setIsRunning(false);
    }
  };

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(val);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal-content"
        onClick={(e) => e.stopPropagation()}
        style={{ maxWidth: "650px" }}
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
                background: "linear-gradient(135deg, #2563eb 0%, #7c3aed 100%)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Zap size={20} color="#ffffff" />
            </div>
            <div>
              <h2 style={{ fontSize: "1.1rem", fontWeight: "700", color: "#ffffff" }}>
                High-Throughput Batch Recovery Runner
              </h2>
              <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                Process all unrecovered payments concurrently through LangGraph
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
            }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div style={{ padding: "1.75rem", display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          {/* Sliders */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "1.25rem",
              background: "var(--bg-surface-elevated)",
              padding: "1.25rem",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--border-subtle)",
            }}
          >
            <div>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  fontSize: "0.8rem",
                  fontWeight: "600",
                  marginBottom: "0.5rem",
                }}
              >
                <span>Async Concurrency</span>
                <span style={{ color: "var(--accent-primary)" }}>{concurrency} workers</span>
              </div>
              <input
                type="range"
                min={5}
                max={50}
                step={5}
                value={concurrency}
                onChange={(e) => setConcurrency(Number(e.target.value))}
                disabled={isRunning}
                style={{ width: "100%", accentColor: "var(--accent-primary)" }}
              />
              <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginTop: "0.25rem" }}>
                Parallel graph execution limit
              </div>
            </div>

            <div>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  fontSize: "0.8rem",
                  fontWeight: "600",
                  marginBottom: "0.5rem",
                }}
              >
                <span>LLM Rate Limiter</span>
                <span style={{ color: "#8b5cf6" }}>{llmConcurrency} parallel</span>
              </div>
              <input
                type="range"
                min={1}
                max={15}
                step={1}
                value={llmConcurrency}
                onChange={(e) => setLlmConcurrency(Number(e.target.value))}
                disabled={isRunning}
                style={{ width: "100%", accentColor: "#8b5cf6" }}
              />
              <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginTop: "0.25rem" }}>
                Protects Gemini API rate limits
              </div>
            </div>
          </div>

          {/* Results Display */}
          {isRunning && (
            <div
              style={{
                background: "rgba(59, 130, 246, 0.08)",
                border: "1px solid rgba(59, 130, 246, 0.3)",
                borderRadius: "var(--radius-md)",
                padding: "1.5rem",
                textAlign: "center",
              }}
            >
              <div
                style={{
                  width: "32px",
                  height: "32px",
                  border: "3px solid #3b82f6",
                  borderTopColor: "transparent",
                  borderRadius: "50%",
                  animation: "spin 1s linear infinite",
                  margin: "0 auto 1rem",
                }}
              />
              <div style={{ fontWeight: "700", color: "#ffffff", marginBottom: "0.25rem" }}>
                Running Autonomous Recovery Agent...
              </div>
              <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                Evaluating policy guardrails, calling gateway retries, and recording state sync
              </div>
            </div>
          )}

          {error && (
            <div
              style={{
                background: "var(--color-danger-bg)",
                border: "1px solid var(--color-danger-border)",
                borderRadius: "var(--radius-md)",
                padding: "1rem",
                color: "#f87171",
                fontSize: "0.85rem",
              }}
            >
              <strong>Error: </strong> {error}
            </div>
          )}

          {result && !isRunning && (
            <div
              style={{
                background: "rgba(16, 185, 129, 0.08)",
                border: "1px solid rgba(16, 185, 129, 0.3)",
                borderRadius: "var(--radius-md)",
                padding: "1.25rem",
                display: "flex",
                flexDirection: "column",
                gap: "1rem",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <Sparkles size={20} color="#10b981" />
                <h3 style={{ fontSize: "1rem", fontWeight: "700", color: "#ffffff" }}>
                  Batch Recovery Run Completed!
                </h3>
              </div>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(3, 1fr)",
                  gap: "0.75rem",
                  textAlign: "center",
                }}
              >
                <div
                  style={{
                    background: "var(--bg-surface)",
                    padding: "0.75rem",
                    borderRadius: "6px",
                  }}
                >
                  <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", textTransform: "uppercase" }}>
                    Recovered Revenue
                  </div>
                  <div style={{ fontSize: "1.15rem", fontWeight: "800", color: "#10b981" }}>
                    {formatCurrency(result.revenue_recovered)}
                  </div>
                </div>

                <div
                  style={{
                    background: "var(--bg-surface)",
                    padding: "0.75rem",
                    borderRadius: "6px",
                  }}
                >
                  <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", textTransform: "uppercase" }}>
                    Payments Saved
                  </div>
                  <div style={{ fontSize: "1.15rem", fontWeight: "800", color: "#ffffff" }}>
                    {result.recovered} / {result.total}
                  </div>
                </div>

                <div
                  style={{
                    background: "var(--bg-surface)",
                    padding: "0.75rem",
                    borderRadius: "6px",
                  }}
                >
                  <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", textTransform: "uppercase" }}>
                    Throughput
                  </div>
                  <div style={{ fontSize: "1.15rem", fontWeight: "800", color: "#60a5fa" }}>
                    {result.throughput_per_sec.toFixed(1)} /s
                  </div>
                </div>
              </div>

              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  fontSize: "0.75rem",
                  color: "var(--text-secondary)",
                }}
              >
                <span>Avg Node Latency: {result.avg_latency_ms.toFixed(1)}ms</span>
                <span>Elapsed: {result.elapsed_seconds.toFixed(2)}s</span>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div
          style={{
            padding: "1.25rem 1.75rem",
            borderTop: "1px solid var(--border-subtle)",
            display: "flex",
            alignItems: "center",
            justifyContent: "flex-end",
            gap: "0.75rem",
          }}
        >
          <button className="btn btn-secondary" onClick={onClose} disabled={isRunning}>
            Close
          </button>
          <button
            className="btn btn-primary"
            onClick={handleStart}
            disabled={isRunning}
            style={{
              background: "linear-gradient(135deg, #2563eb 0%, #7c3aed 100%)",
            }}
          >
            <Zap size={14} />
            <span>{isRunning ? "Processing Batch..." : "Execute Batch Run"}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
