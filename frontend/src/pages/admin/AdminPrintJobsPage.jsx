import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { getAdminPrintJobs } from "../../api/admin.js";
import { useAuth } from "../../context/AuthContext.jsx";
import AdminLayout from "./AdminLayout.jsx";

function formatDateTime(value) {
  if (!value) return "-";
  try {
    return new Date(value).toLocaleString("pl-PL");
  } catch {
    return String(value);
  }
}

const PRINT_JOB_STATUSES = [
  { value: "", label: "Wszystkie" },
  { value: "queued", label: "queued" },
  { value: "printing", label: "printing" },
  { value: "done", label: "done" },
  { value: "failed", label: "failed" },
];

export default function AdminPrintJobsPage() {
  const { token } = useAuth();
  const [limit] = useState(20);
  const [offset, setOffset] = useState(0);
  const [status, setStatus] = useState("");

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const page = useMemo(() => Math.floor(offset / limit) + 1, [offset, limit]);
  const totalPages = useMemo(() => {
    const total = data?.total ?? 0;
    return Math.max(1, Math.ceil(total / limit));
  }, [data, limit]);

  async function load(requestOffset = offset) {
    setLoading(true);
    setError(null);
    try {
      const result = await getAdminPrintJobs({
        token,
        status: status || null,
        limit,
        offset: requestOffset,
      });
      setData(result);
    } catch (e) {
      setError(e.message || "Nie udało się pobrać kolejki wydruków.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [offset]);

  async function applyFilters() {
    setOffset(0);
    await load(0);
  }

  return (
    <AdminLayout
      title="Kolejka wydruków"
      subtitle="Podgląd zleceń druku oraz ich statusów."
      activeHref="/admin/print-jobs"
    >

      {error && (
        <div className="status-card alert" role="alert">
          {error}
        </div>
      )}

      <div className="form-card">
        <div className="field-row">
          <label className="field">
            <span>Status</span>
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              {PRINT_JOB_STATUSES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </label>
          <div className="field" style={{ alignSelf: "end" }}>
            <div className="actions" style={{ marginTop: 0 }}>
              <button type="button" className="primary-button" onClick={applyFilters}>
                Zastosuj
              </button>
              <button
                type="button"
                className="secondary-button"
                onClick={() => {
                  setStatus("");
                  setOffset(0);
                }}
              >
                Wyczyść
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="minor-table-card">
        <div className="minor-table-header">
          <h3>Print jobs</h3>
          <p className="hint" style={{ margin: 0 }}>
            Total: {data?.total ?? 0}
          </p>
        </div>

        {loading ? (
          <p style={{ margin: 0 }}>Ładowanie…</p>
        ) : data?.items?.length ? (
          <div className="admin-table-scroll">
            <table className="minor-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Status</th>
                  <th>Copies</th>
                  <th>Attempts</th>
                  <th>Queued at</th>
                  <th>Submission</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((j) => (
                  <tr key={j.id}>
                    <td className="admin-mono">{String(j.id).slice(0, 8)}…</td>
                    <td>
                      {j.status === "queued"
                        ? "W kolejce"
                        : j.status === "printing"
                          ? "W trakcie"
                          : j.status === "done"
                            ? "Zakończone"
                            : j.status === "failed"
                              ? "Błąd"
                              : j.status}
                    </td>
                    <td>{j.copies}</td>
                    <td>{j.attempts}</td>
                    <td>{formatDateTime(j.queued_at)}</td>
                    <td className="admin-mono">
                      {j.submission?.id ? (
                        <Link to={`/admin/submissions/${j.submission.id}`}>
                          {String(j.submission.id).slice(0, 8)}…
                        </Link>
                      ) : (
                        String(j.submission_id).slice(0, 8) + "…"
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p style={{ margin: 0 }}>Brak wyników.</p>
        )}

        <div className="actions" style={{ justifyContent: "space-between" }}>
          <button
            type="button"
            className="secondary-button"
            disabled={offset <= 0}
            onClick={() => setOffset(Math.max(0, offset - limit))}
          >
            &larr; Poprzednia
          </button>
          <span className="hint" style={{ alignSelf: "center" }}>
            Strona {page} / {totalPages}
          </span>
          <button
            type="button"
            className="secondary-button"
            disabled={data ? offset + limit >= data.total : true}
            onClick={() => setOffset(offset + limit)}
          >
            Następna &rarr;
          </button>
        </div>
      </div>
    </AdminLayout>
  );
}

