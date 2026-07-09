import { useEffect, useState } from "react";
import { getAdminDashboard } from "../../api/admin.js";
import { todaySequenceDate } from "../../lib/adminFilters.js";
import { useAuth } from "../../context/AuthContext.jsx";
import AdminLayout from "./AdminLayout.jsx";

function StatCard({ label, value, hint }) {
  return (
    <div className="admin-stat-card">
      <p className="admin-stat-label">{label}</p>
      <p className="admin-stat-value">{value}</p>
      {hint ? <p className="hint admin-stat-hint">{hint}</p> : null}
    </div>
  );
}

export default function AdminHome() {
  const { token } = useAuth();
  const [sequenceDate, setSequenceDate] = useState(todaySequenceDate);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  async function load(requestDate = sequenceDate) {
    setLoading(true);
    setError(null);
    try {
      const result = await getAdminDashboard({ token, sequenceDate: requestDate });
      setData(result);
    } catch (e) {
      setError(e.message || "Nie udało się pobrać statystyk dnia.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function applyDate() {
    await load(sequenceDate);
  }

  return (
    <AdminLayout
      title="Pulpit dnia"
      subtitle="Podsumowanie zgłoszeń i wydruków dla wybranego dnia wyścigowego."
      activeHref="/admin"
    >
      {error && (
        <div className="status-card alert" role="alert">
          {error}
        </div>
      )}

      <div className="form-card">
        <div className="field-row">
          <label className="field">
            <span>Data dnia</span>
            <input
              type="date"
              value={sequenceDate}
              onChange={(e) => setSequenceDate(e.target.value)}
            />
          </label>
          <div className="field" style={{ alignSelf: "end" }}>
            <div className="actions" style={{ marginTop: 0 }}>
              <button type="button" className="primary-button" onClick={applyDate}>
                Odśwież
              </button>
              <button
                type="button"
                className="secondary-button"
                onClick={() => {
                  const today = todaySequenceDate();
                  setSequenceDate(today);
                  load(today);
                }}
              >
                Dzisiaj
              </button>
            </div>
          </div>
        </div>
      </div>

      {loading ? (
        <p className="status-card">Ładowanie…</p>
      ) : data ? (
        <>
          <div className="admin-stat-grid">
            <StatCard label="Zgłoszenia łącznie" value={data.total_submissions} />
            <StatCard label="Wydrukowane" value={data.print_done_count} />
            <StatCard label="W kolejce" value={data.print_queued_count} />
            <StatCard label="Błąd druku" value={data.print_failed_count} />
            <StatCard
              label="Ostatni nr startowy"
              value={data.last_start_number ?? "—"}
            />
            <StatCard label="Gość" value={data.guest_count} hint="Tryb guest" />
            <StatCard label="Konto" value={data.account_count} hint="Tryb account" />
            <StatCard label="Zgłoszone (bez druku)" value={data.submitted_count} />
          </div>
        </>
      ) : null}
    </AdminLayout>
  );
}
