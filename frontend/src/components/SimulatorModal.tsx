import React, { useState } from "react";
import type { FailureCode, Transaction } from "../types";
import { Sliders, X, Play, CheckCircle2 } from "lucide-react";

interface SimulatorModalProps {
  isOpen: boolean;
  onClose: () => void;
  onInject: (data: {
    amount: number;
    failure_code: string;
    customer_email?: string;
  }) => Promise<Transaction>;
  onSelectPayment: (payment: Transaction) => void;
}

export const SimulatorModal: React.FC<SimulatorModalProps> = ({
  isOpen,
  onClose,
  onInject,
  onSelectPayment,
}) => {
  const [amount, setAmount] = useState(4999);
  const [failureCode, setFailureCode] = useState<FailureCode>("BANK_TIMEOUT");
  const [customerEmail, setCustomerEmail] = useState("rohit.sharma@example.com");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [createdTx, setCreatedTx] = useState<Transaction | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      const tx = await onInject({
        amount: Number(amount),
        failure_code: failureCode,
        customer_email: customerEmail,
      });
      setCreatedTx(tx);
    } catch (err) {
      console.error("Failed to inject failure", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal-content"
        onClick={(e) => e.stopPropagation()}
        style={{ maxWidth: "560px" }}
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
                background: "rgba(245, 158, 11, 0.15)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Sliders size={20} color="#f59e0b" />
            </div>
            <div>
              <h2 style={{ fontSize: "1.1rem", fontWeight: "700", color: "#ffffff" }}>
                Payment Gateway Failure Simulator
              </h2>
              <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                Inject synthetic payment failures to test agent edge cases
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

        {/* Form */}
        <form onSubmit={handleSubmit} style={{ padding: "1.75rem", display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          <div>
            <label
              style={{
                display: "block",
                fontSize: "0.8rem",
                fontWeight: "600",
                color: "var(--text-secondary)",
                marginBottom: "0.4rem",
              }}
            >
              Payment Amount (INR ₹)
            </label>
            <input
              type="number"
              min={100}
              max={1000000}
              value={amount}
              onChange={(e) => setAmount(Number(e.target.value))}
              style={{
                width: "100%",
                background: "var(--bg-surface-elevated)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "var(--radius-md)",
                padding: "0.6rem 0.85rem",
                color: "#ffffff",
                fontSize: "0.9rem",
              }}
            />
          </div>

          <div>
            <label
              style={{
                display: "block",
                fontSize: "0.8rem",
                fontWeight: "600",
                color: "var(--text-secondary)",
                marginBottom: "0.4rem",
              }}
            >
              Failure Error Code
            </label>
            <select
              value={failureCode}
              onChange={(e) => setFailureCode(e.target.value as FailureCode)}
              style={{
                width: "100%",
                background: "var(--bg-surface-elevated)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "var(--radius-md)",
                padding: "0.6rem 0.85rem",
                color: "#ffffff",
                fontSize: "0.9rem",
              }}
            >
              <option value="BANK_TIMEOUT">BANK_TIMEOUT (High recovery probability ~85%)</option>
              <option value="NETWORK_ERROR">NETWORK_ERROR (Temporary glitch ~80%)</option>
              <option value="INSUFFICIENT_FUNDS">INSUFFICIENT_FUNDS (Customer notification trigger ~65%)</option>
              <option value="EXPIRED_CARD">EXPIRED_CARD (Payment link update required ~50%)</option>
              <option value="CARD_DECLINED">CARD_DECLINED (Issuer decline ~40%)</option>
              <option value="FRAUD_RISK">FRAUD_RISK (POLICY ENGINE HARD BLOCK: 0% retry)</option>
              <option value="UNKNOWN">UNKNOWN (Triggers Google Gemini 2.0 Flash classification)</option>
            </select>
          </div>

          <div>
            <label
              style={{
                display: "block",
                fontSize: "0.8rem",
                fontWeight: "600",
                color: "var(--text-secondary)",
                marginBottom: "0.4rem",
              }}
            >
              Customer Email
            </label>
            <input
              type="email"
              value={customerEmail}
              onChange={(e) => setCustomerEmail(e.target.value)}
              style={{
                width: "100%",
                background: "var(--bg-surface-elevated)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "var(--radius-md)",
                padding: "0.6rem 0.85rem",
                color: "#ffffff",
                fontSize: "0.9rem",
              }}
            />
          </div>

          {createdTx && (
            <div
              style={{
                background: "rgba(16, 185, 129, 0.08)",
                border: "1px solid rgba(16, 185, 129, 0.3)",
                borderRadius: "var(--radius-md)",
                padding: "1rem",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <CheckCircle2 size={18} color="#10b981" />
                <span style={{ fontSize: "0.85rem", color: "#ffffff" }}>
                  Injected <strong>{createdTx.id}</strong> (Status: {createdTx.status})
                </span>
              </div>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => {
                  onSelectPayment(createdTx);
                  onClose();
                }}
              >
                Inspect Trace
              </button>
            </div>
          )}

          {/* Footer */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "flex-end",
              gap: "0.75rem",
              marginTop: "0.5rem",
            }}
          >
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
              <Play size={14} />
              <span>{isSubmitting ? "Injecting..." : "Inject Failure"}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
