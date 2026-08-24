import { useState, useEffect, useCallback } from "react";
import { Navbar } from "./components/Navbar";
import { MetricsOverview } from "./components/MetricsOverview";
import { AgentGraphVisualizer } from "./components/AgentGraphVisualizer";
import { AnalyticsCharts } from "./components/AnalyticsCharts";
import { TransactionTable } from "./components/TransactionTable";
import { PaymentDetailModal } from "./components/PaymentDetailModal";
import { BatchRecoveryModal } from "./components/BatchRecoveryModal";
import { SimulatorModal } from "./components/SimulatorModal";
import { api } from "./services/api";
import type {
  Transaction,
  AnalyticsSummary,
  FailureBreakdown,
  DailyTrend,
} from "./types";

export function App() {
  // State
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [failureBreakdown, setFailureBreakdown] = useState<FailureBreakdown[]>([]);
  const [dailyTrends, setDailyTrends] = useState<DailyTrend[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [totalTx, setTotalTx] = useState(0);

  // Filters & Pagination
  const [page, setPage] = useState(1);
  const pageSize = 15;
  const [statusFilter, setStatusFilter] = useState("");
  const [failureFilter, setFailureFilter] = useState("");
  const [searchQuery, setSearchQuery] = useState("");

  // Loading States
  const [loadingMetrics, setLoadingMetrics] = useState(true);
  const [loadingTable, setLoadingTable] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isSeeding, setIsSeeding] = useState(false);
  const [recoveringPaymentId, setRecoveringPaymentId] = useState<string | undefined>(undefined);
  const [activeGraphNode, setActiveGraphNode] = useState<string | undefined>(undefined);

  // Modals
  const [selectedPayment, setSelectedPayment] = useState<Transaction | null>(null);
  const [isBatchModalOpen, setIsBatchModalOpen] = useState(false);
  const [isSimulatorOpen, setIsSimulatorOpen] = useState(false);

  // Notification Toast
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4000);
  };

  // Fetch Analytics & Trends
  const fetchAnalytics = useCallback(async () => {
    try {
      setLoadingMetrics(true);
      const [sum, failData, trends] = await Promise.all([
        api.getAnalyticsSummary().catch(() => null),
        api.getFailureBreakdown().catch(() => []),
        api.getDailyTrends(14).catch(() => []),
      ]);
      if (sum) setSummary(sum);
      if (failData) setFailureBreakdown(failData);
      if (trends) setDailyTrends(trends);
    } catch (err) {
      console.error("Failed to load analytics", err);
    } finally {
      setLoadingMetrics(false);
    }
  }, []);

  // Fetch Payments Table
  const fetchPayments = useCallback(async () => {
    try {
      setLoadingTable(true);
      const offset = (page - 1) * pageSize;
      const res = await api.getPayments({
        status: statusFilter || undefined,
        failure_code: failureFilter || undefined,
        search: searchQuery || undefined,
        limit: pageSize,
        offset,
      });
      setTransactions(res.items || []);
      setTotalTx(res.total || 0);
    } catch (err) {
      console.error("Failed to load payments", err);
    } finally {
      setLoadingTable(false);
    }
  }, [page, pageSize, statusFilter, failureFilter, searchQuery]);

  // Initial Load & Polling
  useEffect(() => {
    fetchAnalytics();
    fetchPayments();
  }, [fetchAnalytics, fetchPayments]);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await Promise.all([fetchAnalytics(), fetchPayments()]);
    setIsRefreshing(false);
    showToast("Dashboard refreshed with latest state");
  };

  const handleSeedData = async () => {
    setIsSeeding(true);
    try {
      const res = await api.seedDataset({ n_customers: 100, n_payments: 300 });
      showToast(`Database seeded: ${res.payments} failed transactions generated`);
      await handleRefresh();
    } catch (err: any) {
      showToast(`Seeding error: ${err.message}`);
    } finally {
      setIsSeeding(false);
    }
  };

  const handleRecoverPayment = async (paymentId: string) => {
    setRecoveringPaymentId(paymentId);

    // Simulate animated node transitions in the visualizer during execution
    setActiveGraphNode("ingestion");
    setTimeout(() => setActiveGraphNode("risk_analysis"), 200);
    setTimeout(() => setActiveGraphNode("root_cause_classification"), 400);
    setTimeout(() => setActiveGraphNode("recovery_decision"), 600);
    setTimeout(() => setActiveGraphNode("policy_engine"), 800);
    setTimeout(() => setActiveGraphNode("action_execution"), 1000);
    setTimeout(() => setActiveGraphNode("outcome_evaluation"), 1200);

    try {
      const res = await api.recoverSinglePayment(paymentId);
      showToast(
        res.final_state.recovered
          ? `🎉 Recovered ₹${res.final_state.revenue_recovered} for ${paymentId}`
          : `Recovery finished: ${res.final_state.status} (${res.final_state.decision_reason})`
      );
      await Promise.all([fetchAnalytics(), fetchPayments()]);

      // If modal was open, refresh selected payment
      if (selectedPayment?.id === paymentId) {
        const updated = await api.getPaymentDetail(paymentId);
        setSelectedPayment(updated);
      }
    } catch (err: any) {
      showToast(`Recovery execution error: ${err.message}`);
    } finally {
      setRecoveringPaymentId(undefined);
      setTimeout(() => setActiveGraphNode(undefined), 1500);
    }
  };

  const handleSelectPayment = async (payment: Transaction) => {
    try {
      const fullDetail = await api.getPaymentDetail(payment.id);
      setSelectedPayment(fullDetail);
    } catch {
      setSelectedPayment(payment);
    }
  };

  return (
    <div className="app-container">
      {/* Toast Notification */}
      {toastMessage && (
        <div
          style={{
            position: "fixed",
            bottom: "24px",
            right: "24px",
            background: "#1e293b",
            border: "1px solid #3b82f6",
            borderRadius: "8px",
            padding: "0.75rem 1.25rem",
            color: "#ffffff",
            fontSize: "0.85rem",
            fontWeight: "600",
            boxShadow: "0 10px 25px rgba(0,0,0,0.5)",
            zIndex: 9999,
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            animation: "fadeIn 0.2s ease",
          }}
        >
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Top Navbar */}
      <Navbar
        onTriggerBatch={() => setIsBatchModalOpen(true)}
        onOpenSimulator={() => setIsSimulatorOpen(true)}
        onSeedData={handleSeedData}
        onRefresh={handleRefresh}
        isRefreshing={isRefreshing}
        isSeeding={isSeeding}
      />

      {/* Main Content */}
      <main className="main-content">
        {/* KPI Metrics */}
        <MetricsOverview summary={summary} loading={loadingMetrics} />

        {/* LangGraph Architecture Pipeline Visualizer */}
        <AgentGraphVisualizer activeNode={activeGraphNode} />

        {/* Analytics Charts */}
        <AnalyticsCharts
          failureData={failureBreakdown}
          dailyTrends={dailyTrends}
          summary={summary}
        />

        {/* Payment Ingestion & Recovery Ledger Table */}
        <TransactionTable
          transactions={transactions}
          total={totalTx}
          loading={loadingTable}
          page={page}
          pageSize={pageSize}
          statusFilter={statusFilter}
          failureFilter={failureFilter}
          searchQuery={searchQuery}
          onPageChange={setPage}
          onStatusFilterChange={(s) => {
            setStatusFilter(s);
            setPage(1);
          }}
          onFailureFilterChange={(f) => {
            setFailureFilter(f);
            setPage(1);
          }}
          onSearchChange={(q) => {
            setSearchQuery(q);
            setPage(1);
          }}
          onSelectPayment={handleSelectPayment}
          onRecoverPayment={handleRecoverPayment}
          recoveringPaymentId={recoveringPaymentId}
        />
      </main>

      {/* Detail Drawer Modal */}
      <PaymentDetailModal
        payment={selectedPayment}
        onClose={() => setSelectedPayment(null)}
        onRecover={handleRecoverPayment}
        isRecovering={recoveringPaymentId === selectedPayment?.id}
      />

      {/* Batch Runner Modal */}
      <BatchRecoveryModal
        isOpen={isBatchModalOpen}
        onClose={() => {
          setIsBatchModalOpen(false);
          handleRefresh();
        }}
        onRunBatch={async (params) => {
          const res = await api.triggerBatchRecovery(params);
          await handleRefresh();
          return res;
        }}
      />

      {/* Simulator Modal */}
      <SimulatorModal
        isOpen={isSimulatorOpen}
        onClose={() => setIsSimulatorOpen(false)}
        onInject={async (data) => {
          const tx = await api.injectFailedPayment(data);
          await handleRefresh();
          return tx;
        }}
        onSelectPayment={handleSelectPayment}
      />
    </div>
  );
}

export default App;
