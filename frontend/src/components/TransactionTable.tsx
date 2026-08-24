import React from "react";
import type { Transaction } from "../types";
import {
  Search,
  Play,
  FileText,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

interface TransactionTableProps {
  transactions: Transaction[];
  total: number;
  loading: boolean;
  page: number;
  pageSize: number;
  statusFilter: string;
  failureFilter: string;
  searchQuery: string;
  onPageChange: (page: number) => void;
  onStatusFilterChange: (status: string) => void;
  onFailureFilterChange: (failure: string) => void;
  onSearchChange: (search: string) => void;
  onSelectPayment: (payment: Transaction) => void;
  onRecoverPayment: (paymentId: string) => void;
  recoveringPaymentId?: string;
}

export const TransactionTable: React.FC<TransactionTableProps> = ({
  transactions,
  total,
  loading,
  page,
  pageSize,
  statusFilter,
  failureFilter,
  searchQuery,
  onPageChange,
  onStatusFilterChange,
  onFailureFilterChange,
  onSearchChange,
  onSelectPayment,
  onRecoverPayment,
  recoveringPaymentId,
}) => {
  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 2,
    }).format(val);
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "RECOVERED":
        return <span className="badge badge-recovered">Recovered</span>;
      case "FAILED":
      case "PENDING_RECOVERY":
        return <span className="badge badge-pending">Pending</span>;
      case "ESCALATED":
        return <span className="badge badge-escalated">Escalated</span>;
      case "EXHAUSTED":
        return <span className="badge badge-failed">Exhausted</span>;
      case "HUMAN_REVIEW":
        return <span className="badge badge-human">Human Review</span>;
      default:
        return <span className="badge badge-pending">{status}</span>;
    }
  };

  const getRiskBadge = (score: number) => {
    let color = "#10b981";
    let text = "LOW";
    if (score >= 0.7) {
      color = "#ef4444";
      text = "HIGH";
    } else if (score >= 0.4) {
      color = "#f59e0b";
      text = "MED";
    }

    return (
      <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
        <div
          style={{
            width: "36px",
            height: "5px",
            background: "var(--bg-surface-elevated)",
            borderRadius: "3px",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              width: `${score * 100}%`,
              height: "100%",
              background: color,
            }}
          />
        </div>
        <span
          style={{
            fontSize: "0.7rem",
            fontWeight: "700",
            color: color,
          }}
        >
          {(score * 100).toFixed(0)}% ({text})
        </span>
      </div>
    );
  };

  const totalPages = Math.ceil(total / pageSize) || 1;

  return (
    <div className="glass-card" style={{ padding: "1.5rem" }}>
      {/* Header & Filters */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "1rem",
          marginBottom: "1.25rem",
        }}
      >
        <div>
          <h2 style={{ fontSize: "1.1rem", fontWeight: "700", color: "#ffffff" }}>
            Payment Ingestion & Recovery Ledger
          </h2>
          <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
            Showing {transactions.length} of {total} failed transactions
          </p>
        </div>

        {/* Filter Controls */}
        <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "0.75rem" }}>
          {/* Search Input */}
          <div
            style={{
              position: "relative",
              display: "flex",
              alignItems: "center",
            }}
          >
            <Search
              size={14}
              color="var(--text-muted)"
              style={{ position: "absolute", left: "10px" }}
            />
            <input
              type="text"
              placeholder="Search ID, customer, email..."
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              style={{
                background: "var(--bg-surface-elevated)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "var(--radius-md)",
                padding: "0.5rem 0.75rem 0.5rem 2rem",
                color: "#ffffff",
                fontSize: "0.8rem",
                outline: "none",
                width: "220px",
              }}
            />
          </div>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => onStatusFilterChange(e.target.value)}
            style={{
              background: "var(--bg-surface-elevated)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-md)",
              padding: "0.5rem 0.75rem",
              color: "#ffffff",
              fontSize: "0.8rem",
              outline: "none",
              cursor: "pointer",
            }}
          >
            <option value="">All Statuses</option>
            <option value="FAILED">FAILED / PENDING</option>
            <option value="RECOVERED">RECOVERED</option>
            <option value="ESCALATED">ESCALATED</option>
            <option value="EXHAUSTED">EXHAUSTED</option>
            <option value="HUMAN_REVIEW">HUMAN REVIEW</option>
          </select>

          {/* Failure Code Filter */}
          <select
            value={failureFilter}
            onChange={(e) => onFailureFilterChange(e.target.value)}
            style={{
              background: "var(--bg-surface-elevated)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-md)",
              padding: "0.5rem 0.75rem",
              color: "#ffffff",
              fontSize: "0.8rem",
              outline: "none",
              cursor: "pointer",
            }}
          >
            <option value="">All Failure Codes</option>
            <option value="BANK_TIMEOUT">BANK_TIMEOUT</option>
            <option value="NETWORK_ERROR">NETWORK_ERROR</option>
            <option value="INSUFFICIENT_FUNDS">INSUFFICIENT_FUNDS</option>
            <option value="EXPIRED_CARD">EXPIRED_CARD</option>
            <option value="CARD_DECLINED">CARD_DECLINED</option>
            <option value="FRAUD_RISK">FRAUD_RISK</option>
          </select>
        </div>
      </div>

      {/* Table Container */}
      <div className="data-table-container">
        <table className="data-table">
          <thead>
            <tr>
              <th>Payment ID</th>
              <th>Customer</th>
              <th>Amount</th>
              <th>Failure Code</th>
              <th>Risk Score</th>
              <th>Retries / Msgs</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={8} style={{ textAlign: "center", padding: "2.5rem" }}>
                  <div style={{ color: "var(--text-secondary)" }}>Loading transactions...</div>
                </td>
              </tr>
            ) : transactions.length === 0 ? (
              <tr>
                <td colSpan={8} style={{ textAlign: "center", padding: "2.5rem" }}>
                  <div style={{ color: "var(--text-muted)", marginBottom: "0.5rem" }}>
                    No payments found matching criteria.
                  </div>
                  <div style={{ fontSize: "0.75rem", color: "var(--text-dim)" }}>
                    Click "Seed 300 Payments" or "Inject Failure" to create data.
                  </div>
                </td>
              </tr>
            ) : (
              transactions.map((tx) => {
                const isRecovering = recoveringPaymentId === tx.id;
                const canRecover = tx.status === "FAILED" || tx.status === "PENDING_RECOVERY";

                return (
                  <tr key={tx.id}>
                    {/* ID */}
                    <td>
                      <span
                        onClick={() => onSelectPayment(tx)}
                        style={{
                          fontFamily: "var(--font-mono)",
                          fontSize: "0.8rem",
                          fontWeight: "600",
                          color: "var(--accent-primary)",
                          cursor: "pointer",
                          textDecoration: "underline",
                        }}
                      >
                        {tx.id}
                      </span>
                    </td>

                    {/* Customer */}
                    <td>
                      <div style={{ display: "flex", flexDirection: "column" }}>
                        <span style={{ fontWeight: "600", fontSize: "0.8rem" }}>
                          {tx.customer?.name || "Customer"}
                        </span>
                        <span style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>
                          {tx.customer?.email || "—"}
                          {tx.customer?.opted_out && (
                            <span style={{ color: "#ef4444", marginLeft: "4px" }}>[OPTED OUT]</span>
                          )}
                        </span>
                      </div>
                    </td>

                    {/* Amount */}
                    <td>
                      <div style={{ fontWeight: "700", fontVariantNumeric: "tabular-nums" }}>
                        {formatCurrency(tx.amount)}
                      </div>
                    </td>

                    {/* Failure Code */}
                    <td>
                      <span
                        style={{
                          background: "var(--bg-surface-elevated)",
                          padding: "0.2rem 0.5rem",
                          borderRadius: "4px",
                          fontSize: "0.725rem",
                          fontFamily: "var(--font-mono)",
                          border: "1px solid var(--border-subtle)",
                          color:
                            tx.failure_code === "FRAUD_RISK"
                              ? "#f87171"
                              : tx.failure_code === "BANK_TIMEOUT"
                              ? "#60a5fa"
                              : "#fde047",
                        }}
                      >
                        {tx.failure_code}
                      </span>
                    </td>

                    {/* Risk Score */}
                    <td>{getRiskBadge(tx.risk_score)}</td>

                    {/* Retries */}
                    <td>
                      <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                        {tx.retry_count} / 3 retries • {tx.message_count} msgs
                      </span>
                    </td>

                    {/* Status */}
                    <td>{getStatusBadge(tx.status)}</td>

                    {/* Actions */}
                    <td>
                      <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
                        {canRecover && (
                          <button
                            className="btn btn-primary btn-sm"
                            onClick={() => onRecoverPayment(tx.id)}
                            disabled={isRecovering}
                            title="Run autonomous recovery graph on this payment"
                          >
                            <Play size={12} />
                            <span>{isRecovering ? "Running..." : "AI Recover"}</span>
                          </button>
                        )}
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={() => onSelectPayment(tx)}
                          title="Inspect LangGraph audit trace and policies"
                        >
                          <FileText size={12} />
                          <span>Audit</span>
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginTop: "1.25rem",
        }}
      >
        <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
          Page {page} of {totalPages} ({total} items total)
        </div>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1}
          >
            <ChevronLeft size={14} />
            <span>Prev</span>
          </button>
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => onPageChange(page + 1)}
            disabled={page >= totalPages}
          >
            <span>Next</span>
            <ChevronRight size={14} />
          </button>
        </div>
      </div>
    </div>
  );
};
