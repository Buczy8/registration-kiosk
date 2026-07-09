import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { getAdminSubmissions, queueSubmissionForPrint } from "../../api/admin.js";
import { downloadPdfBlob } from "../../lib/adminPrint.js";
import { todaySequenceDate } from "../../lib/adminFilters.js";
import { useAuth } from "../../context/AuthContext.jsx";
import AdminLayout from "./AdminLayout.jsx";

function formatDate(value) {
  if (!value) return "-";
  try {
    return new Date(value).toLocaleDateString("pl-PL");
  } catch {
    return String(value);
  }
}

function formatDateTime(value) {
  if (!value) return "-";
  try {
    return new Date(value).toLocaleString("pl-PL");
  } catch {
    return String(value);
  }
}

const SUBMISSION_STATUSES = [
  { value: "", label: "Wszystkie" },
  { value: "submitted", label: "Zgłoszone" },
  { value: "print_queued", label: "W kolejce do druku" },
  { value: "print_done", label: "Wydrukowane" },
  { value: "print_failed", label: "Błąd druku" },
];

function humanizeStatus(value) {
  if (value === "submitted") return "Zgłoszone";
  if (value === "print_queued") return "W kolejce do druku";
  if (value === "print_done") return "Wydrukowane";
  if (value === "print_failed") return "Błąd druku";
  return value;
}

export default function AdminSubmissionsPage() {
  const { token } = useAuth();
  const [limit] = useState(20);
  const [offset, setOffset] = useState(0);

  const [status, setStatus] = useState("");
  const [sequenceDate, setSequenceDate] = useState(todaySequenceDate);

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionMessage, setActionMessage] = useState(null);
  const [actingSubmissionId, setActingSubmissionId] = useState(null);

  const page = useMemo(() => Math.floor(offset / limit) + 1, [offset, limit]);
  const totalPages = useMemo(() => {
    const total = data?.total ?? 0;
    return Math.max(1, Math.ceil(total / limit));
  }, [data, limit]);

  async function load(requestOffset = offset) {
    setLoading(true);
    setError(null);
    try {
      const result = await getAdminSubmissions({
        token,
        status: status || null,
        sequenceDate: sequenceDate || null,
        limit,
        offset: requestOffset,
      });
      setData(result);
    } catch (e) {
      setError(e.message || "Nie udało się pobrać zgłoszeń.");
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

  async function handleQueuePrint(submissionId, startNumber) {
    setActionMessage(null);
    setActingSubmissionId(submissionId);
    try {
      const blob = await queueSubmissionForPrint({ token, submissionId });
      downloadPdfBlob(blob, `wydruk_zgloszenia_${startNumber || submissionId}.pdf`);
      setActionMessage("Plik pobrany do druku.");
      await load();
    } catch (e) {
      setError(e.message || "Nie udało się wydrukować zgłoszenia.");
    } finally {
      setActingSubmissionId(null);
    }
  }

  return (
    <AdminLayout
      title="Zgłoszenia"
      subtitle="Przeglądaj zgłoszenia i drukuj je jednym kliknięciem."
      activeHref="/admin/submissions"
    >

      {error && (
        <div className="status-card alert" role="alert">
          {error}
        </div>
      )}
      {actionMessage && (
        <div className="status-card" role="status">
          {actionMessage}
        </div>
      )}

      <div className="form-card">
        <div className="field-row">
          <label className="field">
            <span>Status</span>
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              {SUBMISSION_STATUSES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Data dnia</span>
            <input
              type="date"
              value={sequenceDate}
              onChange={(e) => setSequenceDate(e.target.value)}
            />
          </label>
        </div>
        <div className="actions">
          <button type="button" className="primary-button" onClick={applyFilters}>
            Filtruj
          </button>
          <button
            type="button"
            className="secondary-button"
            onClick={() => {
              setStatus("");
              setSequenceDate(todaySequenceDate());
              setOffset(0);
              setActionMessage(null);
            }}
          >
            Wyczyść
          </button>
        </div>
      </div>

      <div className="minor-table-card">
        <div className="minor-table-header">
          <h3>Zgłoszenia</h3>
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
                  <th>Imię i nazwisko</th>
                  <th>Start #</th>
                  <th>Sequence</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th style={{ textAlign: "right" }}>Akcje</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((s) => (
                  <tr key={s.id}>
                    <td className="admin-mono">
                      <Link to={`/admin/submissions/${s.id}`}>{String(s.id).slice(0, 8)}…</Link>
                    </td>
                    <td>{s.display_name || "—"}</td>
                    <td>{s.start_number}</td>
                    <td>{formatDate(s.sequence_date)}</td>
                    <td>{humanizeStatus(s.status)}</td>
                    <td>{formatDateTime(s.created_at)}</td>
                    <td>
                      <div className="minor-table-actions">
                        <button
                          type="button"
                          className="secondary-button"
                          disabled={
                            actingSubmissionId === s.id ||
                            s.status === "print_queued" ||
                            s.status === "print_done"
                          }
                          onClick={() => handleQueuePrint(s.id, s.start_number)}
                        >
                          {actingSubmissionId === s.id
                            ? "Drukowanie…"
                            : s.status === "print_queued"
                              ? "W kolejce"
                              : s.status === "print_done"
                                ? "Wydrukowane"
                                : s.status === "print_failed"
                                  ? "Ponów druk"
                                  : "Drukuj"}
                        </button>
                      </div>
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

