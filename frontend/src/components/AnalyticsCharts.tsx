import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import type { FailureBreakdown, DailyTrend, AnalyticsSummary } from "../types";
import { BarChart3, PieChart as PieIcon, LineChart as LineIcon } from "lucide-react";

interface AnalyticsChartsProps {
  failureData: FailureBreakdown[];
  dailyTrends: DailyTrend[];
  summary: AnalyticsSummary | null;
}

const COLORS = ["#10b981", "#3b82f6", "#f59e0b", "#8b5cf6", "#ef4444", "#06b6d4"];

export const AnalyticsCharts: React.FC<AnalyticsChartsProps> = ({
  failureData,
  dailyTrends,
  summary,
}) => {
  const formatCurrency = (val: number) => {
    if (val >= 100000) return `₹${(val / 100000).toFixed(1)}L`;
    if (val >= 1000) return `₹${(val / 1000).toFixed(0)}k`;
    return `₹${val}`;
  };

  const statusDistribution = [
    { name: "Recovered", value: summary?.total_payments_recovered ?? 0, color: "#10b981" },
    { name: "Pending", value: summary?.total_payments_pending ?? 0, color: "#f59e0b" },
    { name: "Escalated", value: summary?.total_payments_escalated ?? 0, color: "#8b5cf6" },
    { name: "Exhausted", value: summary?.total_payments_exhausted ?? 0, color: "#ef4444" },
    { name: "Human Review", value: summary?.total_payments_human_review ?? 0, color: "#06b6d4" },
  ].filter((item) => item.value > 0);

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(480px, 1fr))",
        gap: "1.5rem",
      }}
    >
      {/* 1. Failure Breakdown by Code */}
      <div className="glass-card">
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            marginBottom: "1rem",
          }}
        >
          <BarChart3 size={18} color="#3b82f6" />
          <h3 style={{ fontSize: "0.95rem", fontWeight: "700", color: "#ffffff" }}>
            Payment Failures & Recovery Breakdown
          </h3>
        </div>
        <div style={{ height: "260px", width: "100%" }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={failureData}
              margin={{ top: 10, right: 10, left: -20, bottom: 20 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#1c2b48" />
              <XAxis
                dataKey="failure_code"
                stroke="#64748b"
                tick={{ fill: "#94a3b8", fontSize: 10 }}
                angle={-20}
                textAnchor="end"
              />
              <YAxis stroke="#64748b" tick={{ fill: "#94a3b8", fontSize: 11 }} />
              <Tooltip
                contentStyle={{
                  background: "#0e1526",
                  border: "1px solid #1c2b48",
                  borderRadius: "8px",
                  color: "#f8fafc",
                }}
              />
              <Legend
                wrapperStyle={{ fontSize: "11px", color: "#94a3b8", paddingTop: "5px" }}
              />
              <Bar dataKey="total" name="Total Ingested" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              <Bar dataKey="recovered" name="Successfully Recovered" fill="#10b981" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 2. Cumulative Revenue Trend (14 Days) */}
      <div className="glass-card">
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            marginBottom: "1rem",
          }}
        >
          <LineIcon size={18} color="#10b981" />
          <h3 style={{ fontSize: "0.95rem", fontWeight: "700", color: "#ffffff" }}>
            14-Day Revenue Recovered vs At Risk
          </h3>
        </div>
        <div style={{ height: "260px", width: "100%" }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={dailyTrends}
              margin={{ top: 10, right: 10, left: -10, bottom: 20 }}
            >
              <defs>
                <linearGradient id="riskGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0.0} />
                </linearGradient>
                <linearGradient id="recoveredGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.6} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1c2b48" />
              <XAxis
                dataKey="date"
                stroke="#64748b"
                tick={{ fill: "#94a3b8", fontSize: 10 }}
              />
              <YAxis
                stroke="#64748b"
                tick={{ fill: "#94a3b8", fontSize: 11 }}
                tickFormatter={formatCurrency}
              />
              <Tooltip
                formatter={(val: any) => formatCurrency(Number(val))}
                contentStyle={{
                  background: "#0e1526",
                  border: "1px solid #1c2b48",
                  borderRadius: "8px",
                  color: "#f8fafc",
                }}
              />
              <Legend
                wrapperStyle={{ fontSize: "11px", color: "#94a3b8", paddingTop: "5px" }}
              />
              <Area
                type="monotone"
                dataKey="revenue_at_risk"
                name="Revenue at Risk"
                stroke="#ef4444"
                fillOpacity={1}
                fill="url(#riskGrad)"
              />
              <Area
                type="monotone"
                dataKey="revenue_recovered"
                name="Revenue Recovered"
                stroke="#10b981"
                fillOpacity={1}
                fill="url(#recoveredGrad)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 3. Recovery Rate by Failure Type */}
      <div className="glass-card">
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            marginBottom: "1rem",
          }}
        >
          <BarChart3 size={18} color="#f59e0b" />
          <h3 style={{ fontSize: "0.95rem", fontWeight: "700", color: "#ffffff" }}>
            Recovery Success Rate by Failure Code (%)
          </h3>
        </div>
        <div style={{ height: "260px", width: "100%" }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={failureData}
              layout="vertical"
              margin={{ top: 10, right: 20, left: 30, bottom: 10 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#1c2b48" />
              <XAxis
                type="number"
                domain={[0, 100]}
                unit="%"
                stroke="#64748b"
                tick={{ fill: "#94a3b8", fontSize: 11 }}
              />
              <YAxis
                dataKey="failure_code"
                type="category"
                stroke="#64748b"
                tick={{ fill: "#94a3b8", fontSize: 10 }}
              />
              <Tooltip
                formatter={(val: any) => `${Number(val).toFixed(1)}%`}
                contentStyle={{
                  background: "#0e1526",
                  border: "1px solid #1c2b48",
                  borderRadius: "8px",
                  color: "#f8fafc",
                }}
              />
              <Bar
                dataKey="recovery_rate"
                name="Recovery Rate %"
                fill="#f59e0b"
                radius={[0, 4, 4, 0]}
              >
                {failureData.map((_, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={COLORS[index % COLORS.length]}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 4. Payment Outcomes Distribution */}
      <div className="glass-card">
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            marginBottom: "1rem",
          }}
        >
          <PieIcon size={18} color="#8b5cf6" />
          <h3 style={{ fontSize: "0.95rem", fontWeight: "700", color: "#ffffff" }}>
            Payment Lifecycle Outcomes
          </h3>
        </div>
        <div
          style={{
            height: "260px",
            width: "100%",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {statusDistribution.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={statusDistribution}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={85}
                  paddingAngle={4}
                  dataKey="value"
                  label={({ name, percent }: any) =>
                    `${name} ${(percent * 100).toFixed(0)}%`
                  }
                  labelLine={false}
                >
                  {statusDistribution.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    background: "#0e1526",
                    border: "1px solid #1c2b48",
                    borderRadius: "8px",
                    color: "#f8fafc",
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
              No transactions data available. Seed dataset to see outcomes.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
